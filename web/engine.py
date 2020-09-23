import os
from pyspark.mllib.recommendation import ALS

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_counts_and_averages(ID_and_ratings_tuple):
    """
    取得一组数据的总数和平均值
    returns (bookID, (ratings_count, ratings_avg))
    """
    nratings = len(ID_and_ratings_tuple[1])
    return ID_and_ratings_tuple[0], (nratings, float(sum(x for x in ID_and_ratings_tuple[1]))/nratings)


class RecommendationEngine:
    """
    书籍推荐算法
    """

    def __count_and_average_ratings(self):
        """
        Updates the books ratings counts from
        the current data self.ratings_RDD
        从RDD中更新书籍的评分总量
        """
        logger.info("Counting book ratings...")
        book_ID_with_ratings_RDD = self.ratings_RDD.map(lambda x: (x[1], x[2])).groupByKey()
        book_ID_with_avg_ratings_RDD = book_ID_with_ratings_RDD.map(get_counts_and_averages)
        self.books_rating_counts_RDD = book_ID_with_avg_ratings_RDD.map(lambda x: (x[0], x[1][0]))


    def __train_model(self):
        """
        模型训练
        """
        logger.info("ALS模型训练中...")
        self.model = ALS.train(self.ratings_RDD, self.rank,
                               iterations=self.iterations, lambda_=self.regularization_parameter)
        logger.info("ALS模型训练完成!")

    def __predict_ratings(self, user_and_book_RDD):
        """Gets predictions for a given (userID, bookID) formatted RDD
        Returns: an RDD with format (bookTitle, bookRating, numRatings)
        得到书籍的信息与总评分数
        """
        predicted_RDD = self.model.predictAll(user_and_book_RDD)
        predicted_rating_RDD = predicted_RDD.map(lambda x: (x.product, x.rating))
        predicted_rating_title_and_count_RDD = \
            predicted_rating_RDD.join(self.books_titles_RDD.map(lambda x: (x[0], (x[1], x[2], x[3], x[4], x[5],x[6])))).join(self.books_rating_counts_RDD)
        predicted_rating_title_and_count_RDD = \
            predicted_rating_title_and_count_RDD.map(lambda r: (r[1][0][1][0], r[1][0][1][1], r[1][0][0], r[1][1], r[1][0][1][2], r[1][0][1][3], r[1][0][1][4], r[1][0][1][5]))
        return predicted_rating_title_and_count_RDD

    def __list_to_json(self, ratings):
        #结果序列化
        fields = ['BookID','BookTitle', 'Rating', 'Count', 'BookAuthor', 'Year', 'Publisher', 'URL']
        data = [dict(zip(fields, r)) for r in ratings]
        return data
    
    def add_ratings(self, ratings):
        """
        增加评分
        """
        # Convert ratings to an RDD
        new_ratings_RDD = self.sc.parallelize(ratings)
        # Add new ratings to the existing ones
        self.ratings_RDD = self.ratings_RDD.union(new_ratings_RDD)
        # Re-compute book ratings count
        self.__count_and_average_ratings()
        # Re-train the ALS model with the new ratings
        self.__train_model()
        
        return ratings

    def get_ratings_for_book_ids(self, user_id, book_ids):
        """
        得到用户与书籍信息，经过计算后返回推荐数据
        """
        requested_books_RDD = self.sc.parallelize(book_ids).map(lambda x: (user_id, x))

        ratings = self.__predict_ratings(requested_books_RDD).collect()

        return self.__list_to_json(ratings)
    
    def get_top_ratings(self, user_id, books_count):
        """
        得分最好的书籍
        """
        # Get pairs of (userID, bookID) for user_id unrated books
        user_unrated_books_RDD = self.ratings_RDD.filter(lambda rating: not rating[0] == user_id)\
                                                 .map(lambda x: (user_id, x[1])).distinct()

        # Get predicted ratings
        ratings = self.__predict_ratings(user_unrated_books_RDD).filter(lambda r: r[3]>=25).takeOrdered(books_count, key=lambda x: -x[2])
        # logger.info(ratings)
        return self.__list_to_json(ratings)

    def __init__(self, sc, dataset_path):
        """
        初始化
        """

        logger.info("Starting up the Recommendation Engine: ")

        self.sc = sc

        # 加载评分信息
        logger.info("加载评分数据...")
        ratings_file_path = os.path.join(dataset_path, 'bookrating.csv')
        ratings_raw_RDD = self.sc.textFile(ratings_file_path)
        ratings_raw_data_header = ratings_raw_RDD.take(1)[0]
        self.ratings_RDD = ratings_raw_RDD.filter(lambda line: line!=ratings_raw_data_header)\
            .map(lambda line: line.split(";"))\
            .map(lambda tokens: (int(tokens[0][1:-1]), abs(hash(tokens[1][1:-1])) % (10 ** 8),
                                 int(tokens[2][1:-1]))).cache()
        # 加载书籍信息
        logger.info("加载书籍数据...")
        books_file_path = os.path.join(dataset_path, 'books.csv')
        books_raw_RDD = self.sc.textFile(books_file_path)
        books_raw_data_header = books_raw_RDD.take(1)[0]

        self.books_RDD = books_raw_RDD.filter(lambda line: line!=books_raw_data_header)\
            .map(lambda line: line.split(";"))\
            .map(lambda tokens: (abs(hash(tokens[0][1:-1])) % (10 ** 8), tokens[0][1:-1], tokens[1][1:-1],
                                 tokens[2][1:-1], tokens[3][1:-1], tokens[4][1:-1], tokens[5][1:-1])).cache()

        self.books_titles_RDD = self.books_RDD.map(lambda x: (int(x[0]), x[1], x[2], x[3], x[4], x[5], x[6])).cache()
        self.__count_and_average_ratings()

        # 模型参数
        self.rank = 16
        self.iterations = 10
        self.regularization_parameter = 0.1
        self.__train_model() 
