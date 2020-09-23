# 基于大数据的图书分析系统的设计与实现
------
## 安装方法：
- 推荐使用anaconda自带的python环境，版本3.7.0或者3.6.8
- 在项目文件夹下导入必要的包：
```
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple 
```
- 如提示需要SSL支持，则需要先安装OpenSSL工具：
```
https://slproweb.com/products/Win32OpenSSL.html
```
- 导入数据库文件：配置read_data_save_to_mysql.py中的mysql用户名和密码信息，然后运行：
```
python read_data_save_to_mysql.py
```
- 进入项目文件夹下web目录，启动项目：
```
python server.py
```
- 打开浏览器
```
http://127.0.0.1:8000
```
------
## 项目介绍：

数据来源[http://www2.informatik.uni-freiburg.de/~cziegler/BX/]
Book – Crossing Dataset 是由 Book – Crossing 社区的 278858 名用户的评分组成，其包含约 271379 本书的 1149780 条评分数据，该数据集包含 3 个分类。


* 系统管理员的账号：admin 密码：admin 通过这个账号密码进入后台管理


## 推荐算法思路思路：

本项目实现的图书推荐功能：
+ 热门书籍 
    + 是将评分排名最高的几本书推荐给用户
+ 猜你喜欢
    + 通过数据库SQL语句实现
    + ”看了这本书的人也看了XX书“
    + 主要逻辑是：
        + 首先查该用户的浏览记录
        + 通过浏览过的书籍，找到也看过这本书的人
        + 在也看过这本书的人中，找评分较高的书推荐给用户
+ 推荐书籍
    + 离线计算好的推荐表的信息。使用到了协同过滤算法
    + 计算好的推荐表导入Mysql数据库
    + 通过数据库SQL语句实现
    + 更新推荐表数据需要手动运行python文件更新


## 项目源码介绍


```
----BookRecommendationSystem\
    |----setdatas                 >这个文件夹中存放数据集，数据集比较杂乱。                      
    |----web\                        >web端 
    |    |----logs\                  >日志目录
    |    |----static\                >网页所需的静态文件例如css，js，images
    |    |----templates\             >html文件
    |    |----logger.py               >日志记录
    |    |----config.yml              >配置参数
    |    |----server.py               >项目入口
    |    |----app.py                  >web接口
    |    |----utils.py                >辅助模块
    |----read_data_save_to_mysql.py  >读取data文件夹里面的书籍存储到数据库中
    |----README.md
```