from utils import load_config
from logger import setup_log
from flask import Flask, request, render_template, session, redirect, url_for,Blueprint
from utils import mysql
import math
import json
from engine import RecommendationEngine
main = Blueprint('app', __name__)

config = load_config()
logger = setup_log(__name__)
# main = Flask(__name__)
nextbook = 1;
nextuser = 1;

mysql = mysql(config['mysql'])


@main.route("/")
def root():
    """
    主页
    :return: home.html
    """
    login, userid = False, ''
    if 'userid' in session:
        login, userid = True, session['userid']
    # 热门书籍
    hot_books = []
    # sql: SELECT BookID,sum(Rating) as score FROM Book.Bookrating group by BookID order by score desc limit 10;
    sql = "SELECT BookTitle, BookAuthor ,BookID, ImageM FROM Books where BookID = '" + \
          "' or BookID = '".join(config['bookid']) + "'"

    try:
        hot_books = mysql.fetchall_db(sql)
        hot_books = [[v for k, v in row.items()] for row in hot_books]

    except Exception as e:
        logger.exception("select hot books error: {}".format(e))

    return render_template('Index.html',
                           login=login,
                           books=hot_books,
                           useid=userid,
                           name = "index")


@main.route("/guess")
def guess():
    """
    猜你喜欢
    :return: Index.html
    """
    login, userid, error = False, '', False
    if 'userid' in session:
        login, userid = True, session['userid']
    # 推荐书籍
    guess_books = []
    if login:
        sql = """select e.BookTitle,
                       e.BookAuthor,
                       e.BookID,
                       e.ImageM
                       from Books e
                inner join (select  c.BookID,
                                    sum(c.Rating) as score  
                            from (select UserID,BookID,Rating from Bookrating where Rating != 0
                                limit {0}) c 
                            inner join (select UserID 
                                        from (select UserID,BookID from Bookrating where Rating != 0
                                        limit {0}) a 
                                        inner join (select BookID from Booktuijian where UserID='{1}') b
                                        on a.BookID=b.BookID ) d
                            on c.UserID=d.UserID
                            group by c.BookID 
                            order by score desc 
                            limit 10) f
                on e.BookID = f.BookID""".format(config['limit'], session['userid'])
        try:
            guess_books = mysql.fetchall_db(sql)
            guess_books = [[v for k, v in row.items()] for row in guess_books]

        except Exception as e:
            logger.exception("select guess books error: {}".format(e))
    return render_template('Index.html',
                           login=login,
                           books=guess_books,
                           useid=userid,
                           name = "guess")


@main.route("/recommend")
def recommend():
    """
    推荐页面
    :return: Index.html
    """
    login, userid, error = False, '', False
    if 'userid' in session:
        login, userid = True, session['userid']
    # 推荐书籍
    recommend_books = []
 
    if login:
        sql = """select BookTitle,
                        BookAuthor,
                        a.BookID,
                        a.ImageM ,
                        score
                        from (SELECT * from Books ) a  
                        LEFT  JOIN Booktuijian as b on a.BookID = b.BookID where b.UserID = "{}"
                        order by score desc
                        """.format(userid)
        try:
            recommend_books = mysql.fetchall_db(sql)
            recommend_books = [[v for k, v in row.items()] for row in recommend_books]

        except Exception as e:
            logger.exception("select recommend books error: {}".format(e))
    return render_template('Index.html',
                           login=login,
                           books=recommend_books,
                           useid=userid,
                           name = "recommend")


@main.route("/recommend2")
def recommend2():
    """
    推荐页面
    :return: Index.html
    """
    login, userid, error = False, '', False
    if 'userid' in session:
        login, userid = True, session['userid']
    # 推荐书籍
    top_ratings = []

    if login:
        logger.debug("User %s TOP ratings requested", userid)
        top_ratings = recommendation_engine.get_top_ratings(userid, 5)
        c = [1, 4, 0, 7, 2]
        top_ratings = [[[v for k, v in row.items()][i] for i in c] for row in top_ratings]

    return render_template('Index.html',
                           login=login,
                           books=top_ratings,
                           useid=userid,
                           name = "recommend")

@main.route("/loginForm")
def loginForm():
    """
    跳转登录页
    :return: Login.html
    """
    if 'userid' in session:
        return redirect(url_for('app.root'))
    else:
        return render_template('Login.html', error='')


@main.route("/registerationForm")
def registrationForm():
    """
    跳转注册页
    :return: Register.html
    """
    return render_template("Register.html")


@main.route("/register", methods=["GET", "POST"])
def register():
    """
    注册
    :return: Register.html
    """
    try:
        if request.method == 'POST':
            username = request.form['username']

            try:
                #在此仅仅使用Userid，其他信息写死
                sql = "insert into User (UserID,Location,Age) values ('{}','China','20')".format(username)
                mysql.exe(sql)
            except Exception as e:
                mysql.rollback()
                logger.exception("username:{} register filed".format(username))
            return render_template('Login.html')
    except Exception as e:
        logger.exception("register function error: {}".format(e))
        return render_template('Register.html', error='注册出错')

# 以下部分的请求采用spark的RDD处理，为推荐算法2

@main.route("/<int:user_id>/ratings/top/<int:count>", methods=["GET"])
def top_ratings(user_id, count):
    logger.debug("User %s TOP ratings requested", user_id)
    top_ratings = recommendation_engine.get_top_ratings(user_id, count)
    return json.dumps(top_ratings)


@main.route("/<int:user_id>/ratings/<string:book_id>", methods=["GET"])
def book_ratings(user_id, book_id):
    logger.debug("User %s rating requested for book %s", user_id, book_id)
    hash_book_id = abs(hash(book_id)) % (10 ** 8)
    ratings = recommendation_engine.get_ratings_for_book_ids(user_id, [hash_book_id])
    return json.dumps(ratings)


@main.route("/<int:user_id>/ratings", methods=["POST"])
def add_ratings(user_id):
    # get the ratings from the Flask POST request object
    ratings_list = request.form.keys()[0].strip().split("\n")
    ratings_list = map(lambda x: x.split(","), ratings_list)
    # create a list with the format required by the negine (user_id, book_id, rating)
    ratings = map(lambda x: (user_id, int(x[0]), float(x[1])), ratings_list)
    # add them to the model using then engine API
    recommendation_engine.add_ratings(ratings)

    return json.dumps(ratings)


def create_app(spark_context, dataset_path):
    global recommendation_engine

    recommendation_engine = RecommendationEngine(spark_context, dataset_path)

    app = Flask(__name__)
    app.register_blueprint(main)
    app.config['SECRET_KEY'] = 'chen'
    return app


def is_valid(username):
    """
    登录验证
    :param username: 用户名
    :return: True/False
    """
    try:
        sql = "SELECT UserID as Username FROM User where UserID='{}'".format(username)
        result = mysql.fetchone_db(sql)

        if result:
            logger.info('username:{}: has login success'.format(username))
            return True
        else:
            logger.info('username:{}: has login filed'.format(username))
            return False
    except Exception as e:
        logger.exception('username:{}: has login error'.format(username))
        return False


@main.route("/login", methods=['POST', 'GET'])
def login():
    """
    登录页提交
    :return: Login.html
    """
    if request.method == 'POST':
        username = request.form['username']
        # password = request.form['password']
        if username == 'admin' :
            session['userid'] = username
            return render_template('Admin.html',userid= 'admin')
        if is_valid(username):
            session['userid'] = username
            return redirect(url_for('app.root'))
        else:
            error = '数据库中没有此用户名，请先注册后，然后在此输入，或者重新输入'
            return render_template('Login.html', error=error)


@main.route("/logout")
def logout():
    """
    退出登录，注销
    :return: root
    """
    session.pop('userid', None)
    return redirect(url_for('app.root'))


def update_recommend_book(UserID, BookID):
    """
    更新推荐数据
    """

    sql = '''SELECT score FROM Booktuijian WHERE UserID="{0}" and BookID="{1}"'''.format(UserID, BookID)
    score = mysql.fetchone_db(sql)
    if score:
        score = int(score['score'])
    
        if score + 0.5 > 10: score =10
        else: score += 0.5
        sql = '''UPDATE Booktuijian SET score='{2}' WHERE UserID="{0}" and BookID="{1}" '''.format(UserID, BookID,
                                                                                                   int(score))
        logger.info("update_recommend_book, sql:{}".format(sql))
        mysql.exe(sql)
    else:
        score = 0.5
        sql = ''' insert into Booktuijian (UserID,BookID,score) values ('{0}','{1}','{2}') '''.format(UserID, BookID,
                                                                                                      int(score))
        logger.info("update_recommend_book, sql:{}".format(sql))
        mysql.exe(sql)


@main.route("/bookinfo", methods=['POST', 'GET'])
def bookinfo():
    """
    书籍详情
    :return: BookInfo.html
    """
    # 获取用户IP
    score = 0
    if 'userid' not in session:
        userid = None
        login = False
    else:
        userid = session['userid']
        login = True
    try:
        if request.method == 'GET':
            bookid = request.args.get('bookid')
            sql = """SELECT BookTitle,
                            BookID,
                            PubilcationYear,
                            BookAuthor,
                            ImageM from Books where BookID="{}" """.format(bookid)
            book_info = mysql.fetchall_db(sql)
            book_info = [v for k, v in book_info[0].items()]
            update_recommend_book(userid, bookid)
        if userid:
            sql = '''SELECT Rating FROM Bookrating 
                            where UserID="{}" and BookID="{}"'''.format(userid, bookid)
            score = mysql.fetchone_db(sql)
            if score:
                score = int(score['Rating'])
                score = math.ceil(score / 2)
                if score>10:score=10

    except Exception as e:
        logger.exception("select book info error: {}".format(e))
    return render_template('BookInfo.html',
                           book_info=book_info,
                           login=login,
                           useid=userid,
                           score=score)


@main.route("/user", methods=['POST', 'GET'])
def user():
    """
    个人信息
    :return: UserInfo.html
    """
    login, userid = False, None
    if 'userid' not in session:
        return redirect(url_for('app.loginForm'))
    else:
        login, userid = True, session['userid']
    userinfo = []
    try:
        sql = "select UserID,Location,Age from User where UserID='{}'".format(userid)
        userinfo = mysql.fetchone_db(sql)
        userinfo = [v for k, v in userinfo.items()]
    except Exception as e:
        logger.exception("select UserInfo error: {}".format(e))
    return render_template("UserInfo.html",
                           login=login,
                           useid=userid,
                           userinfo=userinfo)


@main.route("/search", methods=['POST', 'GET'])
def search():
    """
    书籍检索
    :return: Search.html
    """
    login, userid = False, None
    if 'userid' in session:
        login, userid = True, session['userid']
    keyword, search_books = "", []
    try:
        if request.method == 'GET':
            keyword = request.values.get('keyword')
            keyword = keyword.strip()
            sql = "SELECT BookTitle, BookAuthor ,BookID, ImageM from Books where BookTitle like '%{}%' limit 30".format(
                                                                                                                keyword)
            search_books = mysql.fetchall_db(sql)
            search_books = [[v for k, v in row.items()] for row in search_books]
    except Exception as e:
        logger.exception("select search books error: {}".format(e))
    return render_template("Search.html",
                           key=keyword,
                           books=search_books,
                           login=login,
                           useid=userid)


@main.route("/rating", methods=['POST', 'GET'])
def rating():
    """
    书籍评分
    :return: update
    """
    userid = session['userid']
    try:
        if request.method == 'POST':
            rank = request.values.get('rank')
            bookid = request.values.get('book_id')
            sql = '''SELECT COUNT(1) as count FROM Bookrating WHERE UserID="{0}" and BookID="{1}" '''.format(userid,
                                                                                                             bookid)
            count = mysql.fetchone_db(sql)
            if count['count']:
                sql = '''UPDATE Bookrating SET Rating='{2}' WHERE UserID="{0}" and BookID="{1}"  '''.format(userid,
                                                                                                bookid, int(rank) * 2)
            else:
                sql = '''INSERT INTO Bookrating (UserID,BookID,Rating) values ('{0}','{1}','{2}') '''.format(userid,
                                                                                                 bookid, int(rank) * 2)
            mysql.exe(sql)
            logger.info("update book rating success,sql:{}".format(sql))
    except Exception as e:
        logger.exception("rating books error: {}".format(e))
    return redirect(url_for('app.root'))


@main.route("/historical", methods=['POST', 'GET'])
def historical():
    """
    历史评分
    :return: Historicalscore.html"
    """
    login, userid = False, None
    if 'userid' not in session:
        return redirect(url_for('app.loginForm'))
    else:
        login, userid = True, session['userid']
    historicals = []
    try:
        sql = '''SELECT 
                        BookTitle,
                        BookAuthor,
                        PubilcationYear,
                        a.BookID,
                        Rating,
                        ImageM 
                        FROM (SELECT * from Bookrating ) a  
                        LEFT  JOIN  Books as b on a.BookID = b.BookID where a.UserID = '{}'
                        '''.format(userid)
        historicals = mysql.fetchall_db(sql)
        historicals = [[v for k, v in row.items()] for row in historicals]
    except Exception as e:
        logger.exception("historical rating books error: {}".format(e))
    return render_template("Historicalscore.html",
                           books=historicals,
                           login=login,
                           useid=userid)


@main.route("/order", methods=['POST', 'GET'])
def order():
    """
    购物车
    :return: Order.html
    """
    login, userid = False, None
    if 'userid' not in session:
        return redirect(url_for('app.loginForm'))
    else:
        login, userid = True, session['userid']
    cats = []
    try:
        sql = '''SELECT b.BookID,
                        b.BookTitle,
                        b.BookAuthor,
                        floor((b.PubilcationYear-1000)/10) FROM (SELECT * from Cart ) a  
                        LEFT  JOIN  Books as b on a.BookID = b.BookID where a.UserID = "{}"
                        '''.format(userid)
        cats = mysql.fetchall_db(sql)
        cats = [[v for k, v in row.items()] for row in cats]
    except Exception as e:
        logger.exception("historical rating books error: {}".format(e))
    return render_template("Order.html",
                           books=cats,
                           login=login,
                           useid=userid)


#Shopping Cart
@main.route("/addcart", methods=['POST', 'GET'])
def add():
    '''
    添加购物车
    '''
    login, userid = False, None
    if 'userid' not in session:
        return redirect(url_for('app.loginForm'))
    else:
        login, userid = True, session['userid']
    try:
        if request.method == 'GET':
            bookid = request.values.get('bookid')

            sql = '''SELECT COUNT(1) as count FROM Cart WHERE UserID="{0}" and BookID="{1}" '''.format(userid,
                                                                                                       bookid)
            count = mysql.fetchone_db(sql)
            if not count['count']:
                sql = '''INSERT INTO Cart (UserID,BookID ) values ('{0}','{1}') '''.format(userid, bookid)
                mysql.exe(sql)
                logger.info("update Cart  success,sql:{}".format(sql))
    except Exception as e:
        logger.exception("update Cart  books error: {}".format(e))
    return redirect(url_for('app.order'))

@main.route("/delete", methods=['POST', 'GET'])
def delete():
    '''
    删除购物车
    '''
    userid = session['userid']
    try:
        if request.method == 'GET':
            bookid = request.values.get('bookid')
            sql = '''DELETE  FROM Cart WHERE UserID="{0}" and BookID="{1}" '''.format(userid,bookid)
            mysql.exe(sql)
            logger.info("delete Cart  success,sql:{}".format(sql))
    except Exception as e:
        logger.exception("delete Cart  books error: {}".format(e))
    return redirect(url_for('app.order'))


@main.route("/editinfo", methods=["GET", "POST"])
def editinfo():
    """
    修改个人信息
    :return: Userinfo.html
    """
    userid = session['userid']
    try:
        if request.method == 'POST':
            password = request.form['password']
            age = request.form['age']
            try:
                sql = "UPDATE User SET Location='{}',Age= '{}' WHERE UserID='{}'".format(password, age, userid)
                mysql.exe(sql)
                logger.info("UPDATE userinfo --> username:{},password:{},age:{} ".format(userid, password, age))
            except Exception as e:
                mysql.rollback()
                logger.exception("username:{},password:{},age:{} UPDATE filed".format(userid, password, age))
            return redirect(url_for('user'))
    except Exception as e:
        logger.exception("add user info  error: {}".format(e))
        return redirect(url_for('app.user'))


@main.route("/editpassword", methods=["GET", "POST"])
def editpassword():
    """
    修改账号密码
    :return: Userinfo.html
    """
    userid = session['userid']
    try:
        if request.method == 'POST':
            password1 = request.form['password1']
            password2 = request.form['password2']
            if password1==password2:
                try:
                    sql = "UPDATE User SET Location='{}' WHERE UserID='{}'".format(password1, userid)
                    mysql.exe(sql)
                    logger.info("UPDATE password --> username:{},password:{} ".format(userid, password1))
                except Exception as e:
                    mysql.rollback()
                    logger.exception("username:{},password:{} UPDATE password filed".format(userid, password1))
                return redirect(url_for('user'))
    except Exception as e:
        logger.exception("add user info  error: {}".format(e))
        return redirect(url_for('app.user'))

@main.route("/admin")
def admin():
    '''
    后台管理页面的主页面
    '''
    return render_template('Admin.html',userid="admin")


@main.route("/adminuser", methods=["GET", "POST"])
def adminuser():
    '''
    管理用户页面
    '''
    users = []
    try:
        userid = session['userid']
        sql = "select * from User limit 30 "
        users = mysql.fetchall_db(sql)
        users = [[v for k, v in row.items()] for row in users]
        return render_template('AdminUser.html',users = users, error=False, userid=userid)
    except Exception as e:
        logger.exception("Admin User info error: {}".format(e))
        return redirect('AdminUser.html',users = users, error=True, userid="admin")

@main.route("/adminusernextuser", methods=["GET", "POST"])
def adminusernextuser():
    '''
    管理用户页面
    '''
    users = []
    try:
        global nextuser
        userid = session['userid']
        status = 30*nextuser
        sql = "select * from User limit {},30 ".format(status)
        nextuser+=1
        users = mysql.fetchall_db(sql)
        users = [[v for k, v in row.items()] for row in users]
        return render_template('AdminUser.html',users = users, error=False, userid=userid)
    except Exception as e:
        logger.exception("Admin User info error: {}".format(e))
        return redirect('AdminUser.html',users = users, error=True, userid="admin")

@main.route("/keyword", methods=["GET", "POST"])
def keyword():
    '''
    关键字查询用户
    '''
    users = []
    try:
        userid = session['userid']
        if request.method == 'POST':
            keyword = request.form['keyword']
            if keyword:
                sql = "select UserID,Location,Age from User where userid='{}' limit 30 ".format(keyword)
                users = mysql.fetchall_db(sql)
                users = [[v for k, v in row.items()] for row in users]
            return render_template('AdminUser.html',users = users, userid=userid)
    except Exception as e:
        logger.exception("keyword info  error: {}".format(e))
        return render_template('AdminUser.html',users = users, userid="admin")

@main.route("/delete_user", methods=['POST', 'GET'])
def delete_user():
    '''
    删除用户
    '''
    userid = session['userid']
    try:
        if request.method == 'GET':
            userid = request.values.get('userid')
            sql = '''DELETE  FROM User WHERE UserID="{0}" '''.format(userid)
            mysql.exe(sql)
            logger.info("delete User  success,sql:{}".format(sql))
    except Exception as e:
        logger.exception("delete User books error: {}".format(e))
    return redirect(url_for('app.adminuser'))

@main.route("/adminbook", methods=["GET", "POST"])
def adminbook():
    '''
    管理书籍页面
    '''
    userid = session['userid']
    books = []
    try:
        sql = "select * from Books limit 30 "
        books = mysql.fetchall_db(sql)
        books = [[v for k, v in row.items()] for row in books]

    except Exception as e:
        logger.exception("Admin Book info error: {}".format(e))
    return render_template('AdminBook.html',books = books, userid=userid)

@main.route("/adminbooknextpage", methods=["GET", "POST"])
def adminbooknextpage():
    '''
    管理书籍页面
    '''
    userid = session['userid']
    books = []
    try:
        global nextbook
        statue = nextbook*30
        sql = "select * from Books limit {},30".format(statue)
        nextbook+=1
        books = mysql.fetchall_db(sql)
        books = [[v for k, v in row.items()] for row in books]

    except Exception as e:
        logger.exception("Admin Book info error: {}".format(e))
    return render_template('AdminBook.html',books = books, userid=userid)


@main.route("/keyword_book", methods=["GET", "POST"])
def keyword_book():
    '''
    关键字查询书籍
    '''
    books = []
    userid = session['userid']
    try:
        if request.method == 'POST':
            keyword = request.form['keyword']
            if keyword:
                sql = "select * from Books where BookTitle like '%{}%' limit 30 ".format(keyword)
                books = mysql.fetchall_db(sql)
                books = [[v for k, v in row.items()] for row in books]
    except Exception as e:
        logger.exception("keyword info  error: {}".format(e))
    return render_template('AdminBook.html',books = books, userid=userid)

@main.route("/delete_book", methods=['POST', 'GET'])
def delete_book():
    '''
    删除书籍
    '''
    userid = session['userid']
    try:
        if request.method == 'GET':
            bookid = request.values.get('bookid')
            sql = '''DELETE  FROM Books WHERE BookID="{0}" '''.format(bookid)
            mysql.exe(sql)
            logger.info("delete Books  success,sql:{}".format(sql))
    except Exception as e:
        logger.exception("delete books error: {}".format(e))
    return redirect(url_for('app.adminbook'))

@main.route("/addbook", methods=['POST', 'GET'])
def addbook():
    '''
    添加书籍
    '''
    userid = session['userid']
    try:
        if request.method == 'POST':
            bookid = request.form['bookid']
            title = request.form['title']
            author = request.form['author']
            public = request.form['public']
            Image = "http://photocdn.sohu.com/20140424/Img398717878.jpg"
            sql = '''INSERT INTO Books (BookID,BookTitle,BookAuthor,PubilcationYear,Publisher,ImageS,ImageM,ImageL) 
                     values  ('{0}','{1}','{2}','{3}','{4}','{5}','{6}','{7}')'''.format(bookid,title,author,"2018",
                                                                                        public,Image,Image,Image)
            mysql.exe(sql)
            logger.info("add Books  success,sql:{}".format(sql))
            return redirect(url_for('app.adminbook'))
    except Exception as e:
        logger.exception("delete books error: {}".format(e))
    return render_template('AdminAddBook.html')


