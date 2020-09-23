import pymysql
import csv
import codecs

config =  {'user': 'root',
          'password': '123456',
          'port':3306,
          'host': '127.0.0.1',
          'db': 'Book',
          'charset':'utf8'}


def get_conn():
    conn = pymysql.connect(user=config['user'],
                                     password=config['password'],
                                     port=config['port'],
                                     host=config['host'],
                                     db=config['db'],
                                     charset=config['charset'])
    return conn

def query_all(cur, sql, args):
    cur.execute(sql, args)
    return cur.fetchall()


def read_mysql_to_csv(filename,dbname):
    with codecs.open(filename=filename, mode='w', encoding='utf-8') as f:
        write = csv.writer(f, dialect='excel')
        conn = get_conn()
        cur = conn.cursor()
        #sql = cur.execute('select * from \'%s\'')%dbname
        sql = 'select * from {}'.format(dbname)
        results = query_all(cur=cur, sql=sql, args=None)
        for result in results:
            print(result)
            result=result.replace(",","\",\"")
            write.writerow(result)


if __name__ == '__main__':
    read_mysql_to_csv("datasets\\new\\books.csv","books")
    read_mysql_to_csv("datasets\\new\\users.csv","user")
    read_mysql_to_csv("datasets\\new\\bookrating.csv", "bookrating")
    print('数据读取完成')