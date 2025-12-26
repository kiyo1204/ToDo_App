from flask import Flask, render_template, request, redirect,jsonify
from flask import flash
from flask_login import LoginManager, current_user, login_user
from flask_migrate import Migrate
from flask_login import login_required
from flask_login import logout_user
from models import Task, db, User

from datetime import datetime, timedelta, timezone
from flask_apscheduler import APScheduler
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from mail_config import Config


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "mysql+pymysql://db_user:db_password@localhost/app_db"
)
app.secret_key = "deadbeef"
db.init_app(app)
Migrate(app, db)


app.config.from_object(Config)

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()



login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html", title="ユーザ登録")
    else:
        if (
            request.form["id"] == ""
            or request.form["password"] == ""
            or request.form["lastname"] == ""
            or request.form["firstname"] == ""
        ):
            flash("入力されていない項目があります")
            return render_template("register.html", title="ユーザ登録")
        if User.query.get(request.form["id"]) is not None:
            flash("ユーザを登録できません")
            return render_template("register.html", title="ユーザ登録")
        user = User(
            id=request.form["id"],
            password=request.form["password"],
            lastname=request.form["lastname"],
            firstname=request.form["firstname"],
            email=request.form["email"]
        )
        db.session.add(user)
        db.session.commit()
        return redirect("/")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect("/")

    if request.method == "GET":
        return render_template("login.html", title="ログイン")
    else:
        user = User.query.get(request.form["id"])
        if user is not None and user.verify_password(request.form["password"]):
            login_user(user)
            return redirect("/")
        else:
            flash("ユーザIDかパスワードが誤っています")
            return redirect("/login")


@app.route("/logout")
def logout():
    logout_user()
    return redirect("/login")


@app.route("/")
@login_required
def index():
    my_tasks = Task.query.filter_by(user=current_user).order_by(Task.deadline)
    user = User.query.get(current_user.id)
    shared_tasks = Task.query.filter(
        (Task.user != current_user) & Task.is_shared
    ).order_by(Task.deadline)
    my_favorite_tasks = Task.query.filter(
        (Task.user == current_user) & (Task.my_favorite == True)
    ).order_by(Task.deadline)
    
    return render_template(
        "index.html",
        title="ホーム",
        my_tasks=my_tasks,
        shared_tasks=shared_tasks,
        user=user,
        my_favorite_tasks=my_favorite_tasks,
    )


@app.route("/account_delete", methods=["GET", "POST"])
def account_delete():
    Users = User.query.all()
    if request.method == "GET":
        return render_template("account_delete.html", title="アカウント削除")
    else:
        users = User.query.get(request.form["id"])
        for user in Users:
            if user.id is not None and users.verify_password(request.form["password"]):
                tasks = Task.query.filter_by(user=users)
                if tasks is not None:
                    for task in tasks:
                        db.session.delete(task)
                        db.session.commit()
                users = User.query.get(request.form["id"])
                db.session.delete(users)
                db.session.commit()
                return redirect("/")
            else:
                flash("ユーザIDかパスワードが誤っています")
                return redirect("/account_delete")


@app.route("/create", methods=["POST"])
@login_required
def create():
    if request.form["name"] and request.form["deadline"]:
        task = Task(
            user=current_user,
            name=request.form["name"],
            deadline=request.form["deadline"],
            is_shared=request.form.get("is_shared") is not None,
            my_favorite=request.form.get("my_favorite") is not None,
            created_at=datetime.now(timezone(timedelta(hours=+9))),
        )
        Users=User.query.get(current_user.id)

        db.session.add(task)
        db.session.commit()
        
        def send_mail(subject,message,to_email):
    
            mail_user=Config.EMAIL
            mail_password=Config.EMAIL_PASSWORD


            msg=MIMEMultipart()
            msg["From"]=mail_user
            msg["To"]=to_email
            msg["Subject"]=subject
            
            msg.attach(MIMEText(message,"html")) 

            server=smtplib.SMTP_SSL("smtp.gmail.com",465)
            server.ehlo()

            server.login(mail_user,mail_password)

            server.sendmail(mail_user,to_email,msg.as_string())
            server.close()

        Users=User.query.get(current_user.id)
        if Users.email is not None:
            timing_hour=(Users.timing_hours)
            timing_minute=Users.timing_minutes

            deadline=request.form["deadline"]+str(":00")
            date = datetime.strptime(deadline.replace('T', ' '), '%Y-%m-%d %H:%M:%S')+timedelta(hours=-(timing_hour+9))+timedelta(minutes=-(timing_minute))
            subject="リマインド"
            task_name=request.form["name"]
            if timing_hour==0:
                message=task_name+"の締切"+str(timing_minute)+"分前です"
            elif timing_minute==0:
                message=task_name+"の締切"+str(timing_hour)+"時間前です"
            else:
                message=task_name+"の締切"+str(timing_hour)+"時間"+str(timing_minute)+"分前です"
            to_email=Users.email
            message=render_template("email_template.html",message=message,task_name=task_name,id=current_user.firstname,deadline=datetime.strptime(deadline.replace('T', ' '), '%Y-%m-%d %H:%M:%S'))
            try:
                scheduler.add_job(
                id=f"scheduled_email_{to_email}_{date}",
                func=send_mail,
                args=[subject,message,to_email],
                trigger="date",
                run_date=date,
                )
            except Exception as e:
                scheduler.add_job(
                id=f"scheduled_email_{to_email}_{date}_(2)",
                func=send_mail,
                args=[subject,message,to_email],
                trigger="date",
                run_date=date,
                )
    return redirect("/")



@app.route("/update", methods=["GET", "POST"])
@login_required
def update():
    my_tasks = Task.query.filter_by(user=current_user).order_by(Task.deadline)
    task_id = [task.id for task in my_tasks]
    if request.method == "GET":
        return render_template("update.html", title="更新", my_tasks=my_tasks)
    else:
        for id in task_id:
            task = Task.query.get(id)
            task.name = request.form["name_" + str(id)]
            task.deadline = request.form["deadline_" + str(id)]
            task.is_shared = request.form.get("is_shared_" + str(id)) is not None
            task.my_favorite = request.form.get("my_favorite_" + str(id)) is not None
            db.session.commit()
        return redirect("/")


@app.route("/delete", methods=["GET", "POST"])
@login_required
def delete():
    my_tasks = Task.query.filter_by(user=current_user).order_by(Task.deadline)
    tasks_id = request.form.getlist("delete")
    if request.method == "GET":
        return render_template("delete.html", title="削除", my_tasks=my_tasks)
    else:
        for id in tasks_id:
            task = Task.query.get(id)
            db.session.delete(task)
            db.session.commit()
        return redirect("/")

@app.route("/remind_setting", methods=["GET", "POST"])
@login_required
def remind_setting():
    user=User.query.get(current_user.id)
    if request.method=="GET":
        return render_template("remind_setting.html", title="メール設定",user=user)
    else:
        if request.form["email"] is not None:
            user.email=request.form["email"]
            if int(request.form["timing_hours"])<=0 and int(request.form["timing_minutes"])<=0:
                flash("1分以上にしてください")
            elif int(request.form["timing_hours"])<0 or int(request.form["timing_minutes"])<0:
                flash("負数入れないでください")
            else:
                user.timing_hours=request.form["timing_hours"]
                user.timing_minutes=request.form["timing_minutes"]
            db.session.commit()
        return redirect("/")