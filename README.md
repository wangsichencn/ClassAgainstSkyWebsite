# 班级逆天网站
## 使用说明
### 配置
创建 MySQL 数据库
```mysql
CREATE DATABASE classSite;
USE classSite;
```

在 ./university_portal/setting.py 中修改数据库配置
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',      # 使用 mysql 引擎
        'NAME': 'classSite',                    # 你的数据库名（需事先创建）
        'USER': 'root',
        # 'PASSWORD': 'zxh',
        # 'HOST': 'localhost',
        # 'PORT': '3306',
        # 如果使用其他端口或配置，请取消注释并修改以下行
        'PASSWORD': '0000',
        'HOST': 'localhost',
        'PORT': '3307',
    }
}
```
确保与你的 MySQL 配置相同

### 运行
先进行数据迁移
```bash
python manage.py makemigrations
python manage.py migrate 
```

运行程序
```bash
python manage.py runserver
```