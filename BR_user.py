# coding: utf-8 -*-
import math
import pandas as pd

class UserCf:
    # 这个类的主要功能是提供一个基于用户的协调过滤算法接口
    
    def __init__(self):
        self.file_path = './datasets/new/users.csv'
        self._init_frame()

    def _init_frame(self):
        self.frame = pd.read_csv(self.file_path)
        self.frame.columns=['UserID','BookID','Rating'] 

    @staticmethod
    def _cosine_sim(target_books, books):
        '''
        simple method for calculate cosine distance.
        '''
        union_len = len(set(target_books) & set(books))
        if union_len == 0: return 0.0
        product = len(target_books) * len(books)
        cosine = union_len / math.sqrt(product)
        return cosine

    def _get_top_n_users(self, target_user_id, top_n):
        '''
        calculate similarity between all users and return Top N similar users.
        '''
        target_books = self.frame[self.frame['UserID'] == target_user_id]['BookID']
        other_users_id = [i for i in set(self.frame['UserID']) if i != target_user_id]
        other_books = [self.frame[self.frame['UserID'] == i]['BookID'] for i in other_users_id]

        sim_list = [self._cosine_sim(target_books, books) for books in other_books]
        sim_list = sorted(zip(other_users_id, sim_list), key=lambda x: x[1], reverse=True)
        return sim_list[:top_n]

    def _get_candidates_items(self, target_user_id):
        """
        Find all books in source data and target_user did not meet before.
        """
        target_user_books = set(self.frame[self.frame['UserID'] == target_user_id]['BookID'])
        other_user_books = set(self.frame[self.frame['UserID'] != target_user_id]['BookID'])
        candidates_books = list(target_user_books ^ other_user_books)
        return candidates_books

    def _get_top_n_items(self, top_n_users, candidates_books, top_n):
        """
            calculate interest of candidates movies and return top n movies.
        """
        top_n_user_data = [self.frame[self.frame['UserID'] == k] for k, _ in top_n_users]
        interest_list = []
        for book_id in candidates_books:
            tmp = []
            for user_data in top_n_user_data:
                if book_id in user_data['BookID'].values:
                    readdf = user_data[user_data['BookID'] == book_id]
                    tmp.append(round(readdf['Rating'].mean(),2))
                else:
                    tmp.append(0)
            interest = sum([top_n_users[i][1] * tmp[i] for i in range(len(top_n_users))])
            interest_list.append((book_id, interest))
        interest_list = sorted(interest_list, key=lambda x: x[1], reverse=True)
        return interest_list[:top_n]



    def calculate(self, target_user_id, top_n):
        """
        user-cf for books recommendation.
        """
        # most similar top n users
        top_n_users = self._get_top_n_users(target_user_id, top_n)
        # candidates books for recommendation
        candidates_books = self._get_candidates_items(target_user_id)
        # most interest top n books
        top_n_books = self._get_top_n_items(top_n_users, candidates_books, top_n)
        
        print(top_n_books)
        name = []
        values = []
        for x in top_n_books:
            name.append(x[0])
            values.append(x[1])
        df = pd.DataFrame({'UserID':target_user_id,'BookID':name,'score':values})
        return df


def run(i):
    global res
    target_user_id = users[i]
    DF = usercf.calculate(target_user_id, top_n)
    res = res.append(DF)
    

path = './datasets/new/bookrating.csv'
Data = pd.read_csv(path)
Data.columns = ['UserID','BookID','Rating']
res = pd.DataFrame(columns=['UserID','BookID','score'])
usercf = UserCf()

import random
users = [random.choice(list(set(Data['UserID']))) for x in range(20)]
top_n = 10
for x in range(len(users)):
    print(x)
    run(x)
    print(res)
res.to_csv('./datasets/new/booktuijian.csv')

