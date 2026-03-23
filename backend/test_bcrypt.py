import bcrypt

password = "123456"
hash_db = "$2b$12$qHdkDGRrzm/JMgPef99RmuL5ZUAEw7pAqml8SvmBphqyBTg5Ro.HK"

if bcrypt.checkpw(password.encode(), hash_db.encode()):
    print("Match!")
else:
    print("No match!")
