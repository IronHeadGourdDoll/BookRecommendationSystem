
import pymysql
import csv
import codecs

config = {'user': 'root',
          'password': '123456',
          'port': 3306,
          'host': '127.0.0.1',
          'db': 'Book',
          'charset': 'utf8'}

def get_conn():
    conn = pymysql.connect(user=config['user'],
                                     password=config['password'],
                                     port=config['port'],
                                     host=config['host'],
                                     db=config['db'],
                                     charset=config['charset'])
    return conn


def insert(cur, sql, args):
    cur.execute(sql, args)

def truncate(cur, sql, args):
    cur.execute(sql, args)

def read_csv_to_mysql(filename,dbname):
    with codecs.open(filename=filename, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        head = next(reader)
        conn = get_conn()
        cur = conn.cursor()
        sql = 'truncate table booktuijian'
        truncate(cur,sql=sql,args=None)
        sql = 'insert into booktuijian values(%s,%s,%s)'
        for item in reader:
            if item[1] is None or item[1] == '':  # item[1]作为唯一键，不能为null
                continue
            args = tuple(item)
            print(args)
            insert(cur, sql=sql, args=args)

        conn.commit()
        cur.close()
        conn.close()

if __name__ == '__main__':
    read_csv_to_mysql("datasets\\new\\booktuijian.csv")