from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
import hashlib
from os import path, remove, mkdir, listdir


app = Flask(__name__)
# Конфигурацию и модели не стал выносить в отдельный файл, так как это тестовое задание
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

md5 = hashlib.md5()
BASE_DIR = path.dirname(__name__)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer(), primary_key=True)
    base_auth = db.Column(db.String(300), nullable=False, unique=True)
    files = db.relationship("Files", backref="files")

    def __init__(self, base_auth):
        self.base_auth = base_auth

    def __repr__(self):
        return "<{}:{}:{}>".format(self.id, self.base_auth, self.files)


class Files(db.Model):
    __tablename__ = "files"
    id = db.Column(db.Integer(), primary_key=True)
    owner_id = db.Column(db.Integer(), db.ForeignKey("users.id"), nullable=False)
    file_name = db.Column(db.String(300), nullable=False)

    def __init__(self, owner_id, name):
        self.owner_id = owner_id
        self.file_name = name

    def __repr__(self):
        return "<{}:{}>".format(self.id, self.file_name)


@app.route("/upload", methods=["POST"])
def upload_file():
    auth = request.headers.get("Authorization", " ")
    authorized = User.query.filter_by(base_auth=auth).first()

    if authorized:
        if "file" not in request.files:
            return "No file part", 400
        file = request.files["file"]
        if file.filename == "":
            return "No selected file", 400

        # предполагаю, что файл не будет большим и не потребует дополнительной обработки
        data = file.read()
        md5.update(data)
        # если нужно сохранить расширение файла:
        # file_name = (str(md5.hexdigest()) + file.filename[file.filename.rindex('.'):])
        # без сохранения расширения:
        file_name = str(md5.hexdigest())
        dir_path = path.join(*[BASE_DIR, "store", file_name[0:2]])
        if not path.exists:
            mkdir(dir_path)
        else:
            if path.exists(path.join(dir_path, file_name)):
                return "File has already existed", 208
        with open(path.join(dir_path, file_name), "wb") as inf:
            inf.write(data)
        db.session.add(Files(authorized.id, file_name))
        db.session.commit()
        return file_name
    return "Unauthorized", 403


@app.route("/delete", methods=["GET", "POST"])
def delete_file():
    auth = request.headers.get("Authorization", " ")
    file_name = request.args.get("file_name", " ")
    authorized = User.query.filter_by(base_auth=auth).first()

    if authorized:
        # ищем файл и проверяем его хозяина. Если все ок - удаляем
        file = Files.query.filter_by(file_name=file_name).first()
        file_path = path.join(*[BASE_DIR, "store", file_name[0:2], file_name])
        if file.owner_id == authorized.id and path.exists(file_path):
            remove(file_path)
            # проверяем, есть ли еще файлы в данной директории. Если нет - удаляем и ее
            if not listdir(path.join(*[BASE_DIR, "store", file_name[0:2]])):
                remove(path.join(*[BASE_DIR, "store", file_name[0:2]]))
            db.session.delete(file)
            db.session.commit()
            return "Deleted", 200

        return "No such file or this file does not belong to you", 400
    return "Unauthorized", 403


@app.route("/download", methods=["GET"])
def download_file():
    file_name = request.args.get("file_name", " ")
    file_path = path.join(*[BASE_DIR, "store", file_name[0:2], file_name])

    # если такой файл существует - отправляем его
    if path.exists(file_path):
        with open(file_path, "r") as inf:
            data = inf.read()
        return data

    return (
        "Record not found. Try to specify file_name arg or make sure it's correct",
        400,
    )


if __name__ == "__main__":
    app.run(debug=True)
