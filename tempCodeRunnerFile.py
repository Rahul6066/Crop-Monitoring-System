from flask import Flask,render_template,request,session,redirect,url_for,flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash,check_password_hash
from flask_login import login_user,logout_user,login_manager,LoginManager
from flask_login import login_required,current_user
from datetime import datetime
import re 

# MY db connection
local_server= True
app = Flask(__name__)
# Set a strong secret key for session management
app.secret_key='harshithbhaskar'


# this is for getting unique user access
login_manager=LoginManager(app)
login_manager.login_view='login'

@login_manager.user_loader
def load_user(user_id):
    # This function is required by Flask-Login to reload the user object from the user ID stored in the session
    return User.query.get(int(user_id))

# App Configuration
# NOTE: The format is 'mysql://username:password@host/database_name'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/farmers'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Recommended to disable
db=SQLAlchemy(app)

# here we will create db models that is tables

class Farming(db.Model):
    fid=db.Column(db.Integer,primary_key=True)
    farmingtype=db.Column(db.String(100), unique=True) 


class Addagroproducts(db.Model):
    pid=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(50))
    email=db.Column(db.String(50))
    productname=db.Column(db.String(100))
    productdesc=db.Column(db.String(300))
    price=db.Column(db.Numeric(10, 2)) 


class Trig(db.Model):
    # Used for logging trigger actions
    id=db.Column(db.Integer,primary_key=True)
    fid=db.Column(db.String(100)) 
    action=db.Column(db.String(100))
    timestamp=db.Column(db.DateTime, default=datetime.utcnow) 


class User(UserMixin,db.Model):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(50))
    # phone is UNIQUE but now nullable=True to allow email-only signup
    phone=db.Column(db.String(15), unique=True, nullable=True) 
    # email is unique and nullable
    email=db.Column(db.String(50), unique=True, nullable=True) 
    password=db.Column(db.String(250)) 

class Register(db.Model):
    rid=db.Column(db.Integer,primary_key=True)
    farmername=db.Column(db.String(50))
    adharnumber=db.Column(db.String(50), unique=True)
    age=db.Column(db.Integer)
    gender=db.Column(db.String(50))
    phonenumber=db.Column(db.String(50))
    address=db.Column(db.String(250))
    farming=db.Column(db.String(50)) 

# === FIELD MANAGEMENT MODEL (UPDATED) ===
class Field(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    fieldname = db.Column(db.String(100), nullable=False)
    # Removed: location, area, and soiltype
    currentcrop = db.Column(db.String(100), nullable=True) 
    
    unit = db.Column(db.String(10), default='Acre')
    planting_date = db.Column(db.Date, nullable=True)


# --- Utility Function ---

# Function to check if a string is a valid email
def is_email(input_string):
    # Very basic email regex check
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.fullmatch(email_regex, input_string)


# --- Routes ---

@app.route('/')
def index(): 
    return render_template('index.html')


@app.route('/signup',methods=['POST','GET'])
def signup():
    if request.method == "POST":
        username=request.form.get('username')
        login_input=request.form.get('phone_or_email') 
        password=request.form.get('password')

        encpassword=generate_password_hash(password)
        newuser = None
        
        # Determine if the input is an email or phone number
        if is_email(login_input):
            # Case 1: Signup using Email
            user_by_email = User.query.filter_by(email=login_input).first()
            if user_by_email:
                flash("Email Already Registered","warning")
                return render_template('signup.html')
            
            # Create user with Email and NO phone (phone=None is allowed by nullable=True)
            newuser=User(username=username, phone=None, email=login_input, password=encpassword)

        else:
            # Case 2: Signup using Phone Number
            phone_number = ''.join(filter(str.isdigit, login_input))
            if not phone_number or len(phone_number) < 10:
                flash("Invalid Phone Number format. Must contain at least 10 digits.","warning")
                return render_template('signup.html')

            user_by_phone = User.query.filter_by(phone=phone_number).first() 
            if user_by_phone:
                flash("Phone Number Already Registered","warning")
                return render_template('signup.html')
            
            # Create user with Phone and NO email (email=None is allowed by nullable=True)
            newuser=User(username=username, phone=phone_number, email=None, password=encpassword) 
        
        # Only commit if newuser object was successfully created
        if newuser:
            db.session.add(newuser)
            db.session.commit()
            flash("Signup Success! Please Login","success")
            return redirect(url_for('login'))
        else:
            flash("An unexpected error occurred during signup.", "danger")
            return render_template('signup.html')


    return render_template('signup.html')


@app.route('/login',methods=['POST','GET'])
def login():
    if request.method == "POST":
        # Retrieve one field for phone/email
        login_id=request.form.get('phone_or_email') 
        password=request.form.get('password')
        user = None

        # Check if input is a valid email
        if is_email(login_id):
            # Try to look up user by email
            user=User.query.filter_by(email=login_id).first()
        else:
            # Assume it's a phone number and look up user by phone
            # We strip non-digits to handle inputs like (123) 456-7890
            processed_id = ''.join(filter(str.isdigit, login_id))
            user=User.query.filter_by(phone=processed_id).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Login Success","primary")
            return redirect(url_for('index'))
        else:
            flash("Invalid Credentials","warning")
            return render_template('login.html')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logout Successful","warning")
    return redirect(url_for('login'))


# === NEW FIELD ROUTES (UPDATED) ===
@app.route('/add_field', methods=['GET', 'POST'])
@login_required
def add_field():
    if request.method == 'POST':
        # 1. Get ONLY the required data from the form 
        fieldname = request.form.get('field_name')
        currentcrop = request.form.get('crop_planted')
        unit = request.form.get('unit')
        
        # Basic validation (only fieldname is mandatory now)
        if not fieldname: 
            flash("Field Name is required.", "danger")
            return redirect(url_for('add_field'))
        
        try:
            # 2. Create Field object using the updated properties
            new_field = Field(
                user_id=current_user.id,
                fieldname=fieldname,
                # location, area, and soiltype are omitted
                currentcrop=currentcrop if currentcrop else None, 
                unit=unit
            )
            db.session.add(new_field)
            db.session.commit()
            flash(f"Field '{fieldname}' added successfully!", "success")
            return redirect(url_for('view_fields'))
        except Exception as e:
            print(f"Error saving field: {e}")
            flash(f"An error occurred while saving the field: {e}", "danger")
            db.session.rollback()
            return redirect(url_for('add_field'))

    return render_template('add_field.html')

@app.route('/fields')
@login_required
def view_fields():
    # Only show fields belonging to the current user
    fields = Field.query.filter_by(user_id=current_user.id).all()
    # The 'fields' variable is correctly passed to the template here
    return render_template('view_fields.html', fields=fields)


# --- OLDER ROUTES BELOW ---

@app.route('/farmerdetails')
@login_required
def farmerdetails():
    query=Register.query.all()
    return render_template('farmerdetails.html',query=query)

@app.route('/agroproducts')
def agroproducts():
    query=Addagroproducts.query.all()
    return render_template('agroproducts.html',query=query)

@app.route('/addagroproduct',methods=['POST','GET'])
@login_required
def addagroproduct():
    if request.method=="POST":
        username=request.form.get('username')
        email=request.form.get('email')
        productname=request.form.get('productname')
        productdesc=request.form.get('productdesc')
        price=request.form.get('price')
        
        products=Addagroproducts(username=username,email=email,productname=productname,productdesc=productdesc,price=price)
        db.session.add(products)
        db.session.commit()
        flash("Product Added","info")
        return redirect('/agroproducts')
    
    return render_template('addagroproducts.html')

@app.route('/triggers')
@login_required
def triggers():
    query=Trig.query.all()
    return render_template('triggers.html',query=query)

@app.route('/addfarming',methods=['POST','GET'])
@login_required
def addfarming():
    if request.method=="POST":
        farmingtype=request.form.get('farming')
        query=Farming.query.filter_by(farmingtype=farmingtype).first()
        
        if query:
            flash("Farming Type Already Exist","warning")
            return redirect('/addfarming')
            
        dep=Farming(farmingtype=farmingtype)
        db.session.add(dep)
        db.session.commit()
        flash("Farming Added","success")
        return redirect('/addfarming')
        
    return render_template('farming.html')


@app.route("/delete/<string:rid>",methods=['POST','GET'])
@login_required
def delete(rid):
    post=Register.query.filter_by(rid=rid).first()
    
    if post:
        db.session.delete(post)
        db.session.commit()
        flash("Slot Deleted Successfully","warning")
    else:
        flash("Record not found","danger")
        
    return redirect('/farmerdetails')


@app.route("/edit/<string:rid>",methods=['POST','GET'])
@login_required
def edit(rid):
    
    posts=Register.query.filter_by(rid=rid).first()
    farming=Farming.query.all()
    
    if request.method=="POST":
        farmername=request.form.get('farmername')
        adharnumber=request.form.get('adharnumber')
        age=request.form.get('age')
        gender=request.form.get('gender')
        phonenumber=request.form.get('phonenumber')
        address=request.form.get('address')
        farmingtype=request.form.get('farmingtype') 
        
        if posts:
            posts.farmername=farmername
            posts.adharnumber=adharnumber
            posts.age=age
            posts.gender=gender
            posts.phonenumber=phonenumber
            posts.address=address
            posts.farming=farmingtype
            db.session.commit()
            flash("Record Updated","success")
        else:
            flash("Record not found","danger")
            
        return redirect('/farmerdetails')

    return render_template('edit.html',posts=posts,farming=farming)


@app.route('/register',methods=['POST','GET'])
@login_required
def register():
    # Fetch all farming types for the dropdown menu in farmer.html
    farming=Farming.query.all()
    
    if request.method=="POST":
        farmername=request.form.get('farmername')
        adharnumber=request.form.get('adharnumber')
        age=request.form.get('age')
        gender=request.form.get('gender')
        phonenumber=request.form.get('phonenumber')
        address=request.form.get('address')
        farmingtype=request.form.get('farmingtype') 
        
        query=Register(farmername=farmername,adharnumber=adharnumber,age=age,gender=gender,phonenumber=phonenumber,address=address,farming=farmingtype)
        db.session.add(query)
        db.session.commit()
        flash("Your Record Has Been Saved","success")
        return redirect('/farmerdetails')
        
    return render_template('farmer.html',farming=farming)

@app.route('/test')
def test():
    try:
        Register.query.limit(1).all()
        return 'My database is Connected'
    except Exception as e:
        print(f"Database connection error: {e}")
        return 'My db is not Connected'

# --- THE RUN BLOCK (NOW AT THE END) ---
if __name__ == '__main__':
    with app.app_context():
        # db.create_all() MUST run to create the updated 'Field' table columns
        db.create_all() 
        print("Database tables checked/created successfully!") 
    app.run(debug=True)
