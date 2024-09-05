from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.mysql import BIGINT, JSON
import time, requests, json
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from pprint import pprint
from datetime import datetime

app = Flask(__name__)

#configure the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root@localhost/fusion'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'helloworld'

db = SQLAlchemy(app)
jwt = JWTManager(app)


configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = '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'


#function for sending the invite 
# it is called while signup
def send_invite_email(to_email, invite_link):
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    subject = "You're invited!"
    sender = {"email": "prasadabhi95056@gmail.com", "name": "Abhishek"}
    html_content = f"<html><body><p>Click here to join: <a href='{invite_link}'>{invite_link}</a></p></body></html>"
    to = [{"email": to_email}]
    headers = {"Content-Type": "application/json"}

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to, headers=headers, html_content=html_content, sender=sender, subject=subject
    )
    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        pprint(api_response)
    except ApiException as e:
        print(f"Exception when calling Brevo API: {e}")


#This is a function for login alert
#it is called when you login to your account
def send_login_alert(to_email):
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    
    email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        sender={"name": "Abhishek", "email": "prasadabhi95056@gmail.com"},
        subject="Login Alert",
        html_content="<html><body><p>Hello,</p><p>Your account was just logged into. If this was not you, please take appropriate action immediately.</p></body></html>"
    )
    try:
        api_response = api_instance.send_transac_email(email)
        print(f"Login alert email sent successfully! Message ID: {api_response.message_id}")
    except ApiException as e:
        print(f"Failed to send email: {e}")


#This is a function for password update
#it is called when you updaate the password
def send_password_update_alert(to_email):
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    
    email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        sender={"name": "Your App", "email": "prasadabhi95056@gmail.com"},
        subject="Password Update Alert",
        html_content="<html><body><p>Hello,</p><p>Your password has been successfully updated. If this was not you, please reset your password immediately and contact support.</p></body></html>"
    )
    try:
        api_response = api_instance.send_transac_email(email)
        print(f"Password update alert email sent successfully! Message ID: {api_response.message_id}")
    except ApiException as e:
        print(f"Failed to send email: {e}")


#These are the databases schema
class Organization(db.Model):
    __tablename__ = 'organization'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Integer, default=0, nullable=False)
    personal = db.Column(db.Boolean, default=False, nullable=True)
    settings = db.Column(db.JSON, default={}, nullable=True)
    created_at = db.Column(db.BIGINT, nullable=True)
    updated_at = db.Column(db.BIGINT, nullable=True)

    members = db.relationship('Member', backref='organization', lazy=True)
    roles = db.relationship('Role', backref='organization', lazy=True)

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), unique=False, nullable=False)
    profile = db.Column(db.JSON, default={}, nullable=False)
    status = db.Column(db.Integer, default=0, nullable=False)
    settings = db.Column(db.JSON, default={}, nullable=True)
    created_at = db.Column(db.BIGINT, nullable=True)
    updated_at = db.Column(db.BIGINT, nullable=True)

    memberships = db.relationship('Member', backref='user', lazy=True)

class Member(db.Model):
    __tablename__ = 'member'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    org_id = db.Column(db.Integer, db.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    status = db.Column(db.Integer, nullable=False, default=0)
    settings = db.Column(db.JSON, default={}, nullable=True)
    created_at = db.Column(db.BIGINT, nullable=True)
    updated_at = db.Column(db.BIGINT, nullable=True)

    role = db.relationship('Role', backref='members')


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    org_id = db.Column(db.Integer, db.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False)

#calling to create table
with app.app_context():
    db.create_all() 

#From here route has been started

#This is a sign in route
@app.route("/signin",methods=['POST'])
def signin():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    if user and check_password_hash(user.password,data['password']):
        access_token = create_access_token(identity=user.id)
        send_login_alert(user.email)
        return jsonify(access_token=access_token), 200
    return jsonify({"message":"Signin UnSuccessful"}), 401


# This is a signup route
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    hashed_password = generate_password_hash(data['password'])
    new_user = User(
        email=data['email'],
        password = hashed_password,
        profile={},
        status = 1
    )
    db.session.add(new_user)
    db.session.commit()

    new_org = Organization(
        name = data['organization_name'],
        status=1,
        personal = False
    )
    db.session.add(new_org)
    db.session.commit()

    owner_role = Role(
        name = 'owner',
        org_id = new_org.id
    )
    db.session.add(owner_role)
    db.session.commit()

    new_member = Member(
        org_id = new_org.id,
        user_id = new_user.id,
        role_id = owner_role.id
    )
    db.session.add(new_member)
    db.session.commit()

    invite_link = f"https://google.com/invite?user={new_user.id}"
    send_invite_email(new_user.email, invite_link)

    return jsonify({"message":"signup successful"})

@app.route("/signout")
def signout():
    return jsonify({"message": "Signout successful"})


# This is a reset password route
@app.route("/resetpass", methods=["POST"])
@jwt_required()
def resetpass():

    user_id = get_jwt_identity()
    data = request.json

    if not data or 'new_password' not in data:
        return jsonify({"message":"Password is required"})

    new_password = data['new_password']

    user = User.query.get(user_id)
    print(user.email)
    if user:
        user.password = generate_password_hash(new_password)
        db.session.commit()
        send_password_update_alert(user.email)
        return jsonify({"message":"Password updated successfully"})

    return jsonify({"message":"User not found"})


# this is invitation route
@app.route("/invite",methods=["POST"])
@jwt_required()
def invite():

    data = request.json
    email = data['email']
    org_id = data['org_id']
    role_id = data['role_id']

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email,
                password = generate_password_hash('default_password'),
                profile = {},
                status = 1
                )
        
        db.session.add(user)
        db.session.commit()

    member = Member.query.filter_by(user_id=user.id,org_id=org_id).first()
    if member:
        return jsonify({"message":"Member already exists"})
    


    new_member = Member(org_id = org_id,
                        user_id = user.id,
                        role_id=  role_id,
                        status=1,
                        created_at = int(time.time()),
                        updated_at= int(time.time())
                        )
    db.session.add(new_member)
    db.session.commit()    

    return jsonify({"message":"Member invited successfully"})

#This is to delete the route
@app.route("/delete",methods=["POST"])
@jwt_required()
def delt():

    data = request.json
    member_id = data['member_id']

    member = Member.query.get(member_id)
    if member:
        db.session.delete(member)
        db.session.commit()
        return({"message":"Member deleted successfully"})
    return jsonify({"message":"member deleted"})


#This is the update route
@app.route("/update",methods=["POST"])
@jwt_required()
def updt():

    data = request.json
    member_id = data['member_id']
    new_role_id = data['new_role_id']

    member = Member.query.get(member_id)
    if member:
        member.role_id = new_role_id
        db.session.commit()
        return({"message":"Member role updated successfully"})
    return jsonify({"message":"member updated"})


# From here Stats route has been started

#This is role wise user route
@app.route("/stats/role_wise_users",methods=["GET"])
@jwt_required()
def role_wise_user():
    role_count = db.session.query(Role.name,
                                  db.func.count(Member.user_id)
                                  ).join(Member).group_by(Role.name).all()
    
    result = { role: count for role,count in role_count}
    return jsonify(result)

#This is organization wise member
@app.route("/stats/org_wise_member",methods=["GET"])
@jwt_required()
def org_wise_user():
    org_count = db.session.query(
        Organization.name,db.func.count(Member.user_id)
        ).join(Member).group_by(Organization.name).all()
    
    result = {org: count for org,count in org_count}
    return jsonify(result)


#This is organization role wise users filter by datetime
@app.route("/stats/org_role_wise_users", methods=["GET"])
@jwt_required()
def org_role_wise_users():
    from_time = request.args.get('from_time')
    to_time = request.args.get('to_time')
    status = request.args.get('status')

    query = db.session.query(
        Organization.name, Role.name, db.func.count(Member.user_id)
    ).select_from(Member)  

    query = query.join(Organization, Organization.id == Member.org_id)
    query = query.join(Role, Role.id == Member.role_id)

    if from_time and to_time:
        query = query.filter(Member.created_at.between(from_time, to_time))
    if status:
        query = query.filter(Member.status == status)

    query = query.group_by(Organization.name, Role.name)
    result = query.all()

    response = {}
    for org_name, role_name, count in result:
        if org_name not in response:
            response[org_name] = {}
        response[org_name][role_name] = count

    return jsonify(response)

# This is role wise user filter by datetime
@app.route("/stats/role_wise_users", methods=["GET"])
@jwt_required()
def role_wise_users():
    from_time = request.args.get('from_time', None)
    to_time = request.args.get('to_time', None)
    status_filter = request.args.get('status', None)

    query = db.session.query(
        Role.name, db.func.count(Member.user_id)
    ).join(Member).join(User)

    if from_time:
        try:
            from_time = datetime.fromisoformat(from_time)
            query = query.filter(Member.created_at >= from_time)
        except ValueError:
            return jsonify({"message": "Invalid from_time format"}), 400

    if to_time:
        try:
            to_time = datetime.fromisoformat(to_time)
            query = query.filter(Member.created_at <= to_time)
        except ValueError:
            return jsonify({"message": "Invalid to_time format"}), 400

    if status_filter:
        query = query.filter(Member.status == status_filter)

    role_users = query.group_by(Role.name).all()

    result = {role: count for role, count in role_users}
    return jsonify(result)


if __name__ == "__main__":
    app.run()
