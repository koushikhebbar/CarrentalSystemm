from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from pymongo import MongoClient
from bson import Binary, ObjectId
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
import os
import re
import firebase_admin
from firebase_admin import credentials, auth
import razorpay
from pytz import timezone

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secure_secret_key')
app.permanent_session_lifetime = timedelta(minutes=30)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Razorpay configuration
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_Oz82layOlk7wVy')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'aloRrEV8jEHS1f6RGGJ4VmKr')
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Initialize Firebase Admin SDK
firebase_cred = credentials.Certificate('rentigoooo-firebase-adminsdk-fbsvc-6b853eda62.json')
firebase_admin.initialize_app(firebase_cred)
logger.info("Firebase Admin SDK initialized successfully")

# Connect to MongoDB
MONGO_URI = os.environ.get('MONGO_URI', "mongodb+srv://rentigoUser:rentigo115@rentigocluster.pl9ppid.mongodb.net/?retryWrites=true&w=majority&appName=RentigoCluster")
try:
    client = MongoClient(MONGO_URI)
    db = client['rentigo']
    cars_collection = db['cars']
    bookings_collection = db['Bookings']
    notifications_collection = db['notifications']
    users_collection = db['users']  # Added for storing user data
    logger.info("Connected to MongoDB successfully")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {str(e)}")
    raise

# IST timezone
IST = timezone('Asia/Kolkata')

# Allowed vehicle types
ALLOWED_VEHICLE_TYPES = ['car', 'bike', 'scooty']

# Location to address mapping
location_addresses = {
    "Udupi": "123, Temple Street, Udupi, Karnataka 576101",
    "Manipal": "456, University Road, Manipal, Udupi Taluk, Karnataka 576104",
    "Mangalore": "789, Falnir Main Road, Mangalore, Karnataka 575001",
    "Kundapur": "234, Bus Stand Road, Kundapur, Karnataka 576201",
    "Karkala": "890, Main Road, Karkala, Karnataka 574104"
}

# Notification creation function
def create_notification(firebase_uid, action, message, additional_data=None):
    try:
        notification = {
            'firebase_uid': firebase_uid,
            'action': action,
            'message': message,
            'timestamp': datetime.now(IST),
            'read': False,
            'additional_data': additional_data or {},
            'created_at': datetime.utcnow()
        }
        notifications_collection.insert_one(notification)
        logger.info(f"Notification created for Firebase UID {firebase_uid}: {action}")
    except Exception as e:
        logger.error(f"Error creating notification: {str(e)}")

# Get notifications route
@app.route('/get_notifications')
def get_notifications():
    if 'firebase_uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    try:
        notifications = list(notifications_collection.find({'firebase_uid': session['firebase_uid']}).sort('timestamp', -1).limit(10))
        unread_count = notifications_collection.count_documents({'firebase_uid': session['firebase_uid'], 'read': False})
        formatted_notifications = [
            {
                'action': n['action'],
                'message': n['message'],
                'timestamp': n['timestamp'].strftime('%d-%m-%Y %H:%M:%S'),
                'read': n['read']
            } for n in notifications
        ]
        logger.debug(f"Retrieved {len(notifications)} notifications for Firebase UID: {session['firebase_uid']}")
        return jsonify({
            'status': 'success',
            'notifications': formatted_notifications,
            'unread_count': unread_count
        })
    except Exception as e:
        logger.error(f"Error fetching notifications: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Error fetching notifications'}), 500

# Session timeout middleware
@app.before_request
def make_session_permanent():
    session.permanent = True
    if 'firebase_uid' in session:
        last_activity = session.get('last_activity')
        current_time = datetime.utcnow().replace(tzinfo=None)
        
        if last_activity:
            if isinstance(last_activity, str):
                last_activity = datetime.fromisoformat(last_activity).replace(tzinfo=None)
            elif isinstance(last_activity, datetime):
                last_activity = last_activity.replace(tzinfo=None)
            else:
                last_activity = current_time
        
            if (current_time - last_activity) > app.permanent_session_lifetime:
                session.clear()
                flash('Your session has expired. Please login again.', 'danger')
                return redirect(url_for('login'))
        
        session['last_activity'] = current_time.isoformat()
    else:
        session['last_activity'] = datetime.utcnow().replace(tzinfo=None).isoformat()

# Home route
@app.route('/')
def home():
    vehicles = list(cars_collection.find({'available': True}).sort('created_at', -1).limit(3))
    today = datetime.utcnow().date().isoformat()
    max_date = (datetime.utcnow().date() + timedelta(days=30)).isoformat()
    return render_template('home.html', vehicles=vehicles, today=today, max_date=max_date)

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        id_token = data.get('idToken')
        try:
            decoded_token = auth.verify_id_token(id_token)
            uid = decoded_token['uid']
            email = decoded_token.get('email')
            username = decoded_token.get('display_name', email.split('@')[0])
            session['firebase_uid'] = uid
            session['username'] = username
            session['last_activity'] = datetime.utcnow().replace(tzinfo=None).isoformat()
            logger.info(f"User {email} logged in successfully")
            create_notification(
                firebase_uid=uid,
                action='login',
                message=f"You logged in on {datetime.now(IST).strftime('%d-%m-%Y at %H:%M:%S')}.",
                additional_data={'email': email}
            )
            return jsonify({'status': 'success', 'redirect': '/view_cars'})
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash('Invalid token or login failed', 'danger')
            return jsonify({'status': 'error', 'message': 'Invalid token or login failed'}), 401
    return render_template('login.html')

# Forgot password route
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        if not email:
            flash('Please provide an email.', 'danger')
            return render_template('forgot_password.html')
        
        try:
            action_code_settings = {
                'url': 'https://rentigoooo.firebaseapp.com/reset_password',
                'handleCodeInApp': True
            }
            auth.generate_password_reset_link(email, action_code_settings=action_code_settings)
            try:
                user = auth.get_user_by_email(email)
                create_notification(
                    firebase_uid=user.uid,
                    action='password_reset_request',
                    message=f"You requested a password reset on {datetime.now(IST).strftime('%d-%m-%Y at %H:%M:%S')}.",
                    additional_data={'email': email}
                )
            except auth.UserNotFoundError:
                logger.debug(f"No Firebase user found for email: {email}, but reset link sent")
            flash('Password reset link sent to your email.', 'success')
            return redirect(url_for('login'))
        except auth.UserNotFoundError:
            flash('No account found with that email.', 'danger')
            return render_template('forgot_password.html')
        except auth.InvalidEmailError:
            flash('Invalid email format.', 'danger')
            return render_template('forgot_password.html')
        except auth.TooManyAttemptsError:
            flash('Too many reset attempts. Please try again later.', 'danger')
            return render_template('forgot_password.html')
        except Exception as e:
            logger.error(f"Error sending password reset: {type(e).__name__}: {str(e)}")
            flash('Failed to send reset link. Please try again later.', 'danger')
            return render_template('forgot_password.html')
    
    return render_template('forgot_password.html')

# Reset password route
@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        if not email:
            flash('Email required', 'danger')
            return jsonify({'status': 'error', 'message': 'Email required'}), 400
        try:
            user = auth.get_user_by_email(email)
            create_notification(
                firebase_uid=user.uid,
                action='password_reset_success',
                message=f"Your password was reset successfully on {datetime.now(IST).strftime('%d-%m-%Y at %H:%M:%S')}.",
                additional_data={'email': email}
            )
            flash('Password reset successfully. Please login.', 'success')
            return jsonify({'status': 'success', 'message': 'Password reset successfully'})
        except auth.UserNotFoundError:
            flash('User not found', 'danger')
            return jsonify({'status': 'error', 'message': 'User not found'}), 400
        except Exception as e:
            logger.error(f"Error processing password reset: {str(e)}")
            flash('Error processing password reset', 'danger')
            return jsonify({'status': 'error', 'message': 'Error processing password reset'}), 500
    return render_template('reset_password.html')

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        mobile = request.form.get('mobile')
        
        try:
            # Validate inputs
            if not all([username, password, email, mobile]):
                return jsonify({"status": "error", "message": "All fields are required"}), 400
            
            if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
                return jsonify({"status": "error", "message": "Username must be 3–20 characters and contain only letters, numbers, or underscores"}), 400
            
            if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
                return jsonify({"status": "error", "message": "Invalid email format"}), 400
            
            if not re.match(r'^\d{10}$', mobile):
                return jsonify({"status": "error", "message": "Mobile number must be exactly 10 digits"}), 400
            
            if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[a-z]', password) or not re.search(r'[0-9]', password) or not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                return jsonify({"status": "error", "message": "Password must be at least 8 characters and include uppercase, lowercase, number, and special character"}), 400

            # Check for existing username in MongoDB
            if users_collection.find_one({'username': username}):
                return jsonify({"status": "error", "message": "Username already taken"}), 400

            # Check for existing email in Firebase
            try:
                auth.get_user_by_email(email)
                return jsonify({"status": "error", "message": "Email already registered"}), 400
            except auth.UserNotFoundError:
                pass

            # Check for existing mobile number in Firebase
            try:
                auth.get_user_by_phone_number(f'+91{mobile}')
                return jsonify({"status": "error", "message": "Mobile number already registered"}), 400
            except auth.UserNotFoundError:
                pass

            # Create user in Firebase
            user = auth.create_user(
                email=email,
                password=password,
                display_name=username,
                phone_number=f'+91{mobile}'
            )

            # Store user data in MongoDB
            user_data = {
                'firebase_uid': user.uid,
                'username': username,
                'email': email,
                'mobile': mobile,
                'created_at': datetime.utcnow()
            }
            users_collection.insert_one(user_data)

            # Create notification
            create_notification(
                firebase_uid=user.uid,
                action='register',
                message=f"Welcome to Rentigo! You registered on {datetime.now(IST).strftime('%d-%m-%Y at %H:%M:%S')}.",
                additional_data={'username': username, 'email': email}
            )

            logger.info(f"User registered successfully: {email}")
            return jsonify({"status": "success", "redirect": url_for('login')})

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500
    
    return render_template('register.html')

# Logout route
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        username = session.get('username', 'unknown')
        firebase_uid = session.get('firebase_uid')
        if firebase_uid:
            create_notification(
                firebase_uid=firebase_uid,
                action='logout',
                message=f"You logged out on {datetime.now(IST).strftime('%d-%m-%Y at %H:%M:%S')}.",
                additional_data={'username': username}
            )
        session.clear()
        flash('You have been logged out.', 'success')
        return redirect(url_for('home'))
    return render_template('logout.html')

# Booking history route
@app.route('/booking_history')
def booking_history():
    if 'firebase_uid' not in session:
        flash('Please login to view booking history', 'danger')
        return redirect(url_for('login'))
    
    bookings = list(bookings_collection.find({'firebase_uid': session['firebase_uid']}).sort('created_at', -1))
    for booking in bookings:
        booking['vehicle'] = cars_collection.find_one({'_id': booking['vehicle_id']})
    
    logger.debug(f"Retrieved {len(bookings)} bookings for Firebase UID: {session['firebase_uid']}")
    return render_template('booking_history.html', bookings=bookings)

# Search vehicles
@app.route('/search', methods=['POST'])
def search():
    if 'firebase_uid' not in session:
        flash('Please login to search for vehicles', 'danger')
        return redirect(url_for('login'))

    try:
        location = request.form.get('location', '').strip()
        vehicle_type = request.form.get('vehicle_type', 'car').lower()
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        if not location or location not in location_addresses:
            flash('Please select a valid location (Udupi, Manipal, Mangalore, Kundapur, Karkala)', 'danger')
            return render_template('home.html')

        if vehicle_type not in ALLOWED_VEHICLE_TYPES:
            flash('Invalid vehicle type. Must be car, bike, or scooty.', 'danger')
            return render_template('view-cars.html')

        if not start_date_str or not end_date_str:
            flash('Please select both start and end dates.', 'danger')
            return render_template('home.html')

        session['search_params'] = {
            'location': location,
            'location_address': location_addresses[location],
            'vehicle_type': vehicle_type,
            'start_date': start_date_str,
            'end_date': end_date_str
        }

        query = {
            'car_type': vehicle_type,
            'location': {'$regex': location, '$options': 'i'},
            'available': True
        }

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            today = datetime.utcnow().date()
            max_date = today + timedelta(days=30)

            if start_date < today:
                flash('Start date cannot be in the past', 'danger')
                return render_template('view-cars.html')
            if start_date >= end_date:
                flash('End date must be after start date', 'danger')
                return render_template('view-cars.html')
            if start_date > max_date or end_date > max_date:
                flash('Dates must be within 1 month from today.', 'danger')
                return render_template('view-cars.html')
            if start_date.year > 9999 or end_date.year > 9999:
                flash('Year cannot exceed 4 digits.', 'danger')
                return render_template('view-cars.html')

            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.min.time())

            booked_vehicle_ids = [
                booking['vehicle_id']
                for booking in bookings_collection.find({
                    'status': {'$ne': 'cancelled'},
                    '$or': [
                        {'start_date': {'$lte': end_dt}, 'end_date': {'$gte': start_dt}}
                    ]
                })
            ]
            query['_id'] = {'$nin': booked_vehicle_ids}
        except ValueError:
            flash('Invalid date format (use YYYY-MM-DD)', 'danger')
            return render_template('view-cars.html')

        vehicles = list(cars_collection.find(query).sort('created_at', -1))

        if not vehicles:
            flash(f"No {vehicle_type}s available in {location}", 'info')
            logger.info(f"No vehicles found for search: {vehicle_type} in {location}")

        logger.debug(f"Search returned {len(vehicles)} vehicles")
        return render_template('view-cars.html',
                              cars=vehicles,
                              search_params=session['search_params'],
                              today=datetime.utcnow().date().isoformat(),
                              max_date=(datetime.utcnow().date() + timedelta(days=30)).isoformat())
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        flash('An error occurred during search', 'danger')
        return render_template('view-cars.html')

# View all vehicles
@app.route('/view_cars')
def view_cars():
    search_params = session.get('search_params', {})
    query = {'available': True}
    
    cars = list(cars_collection.find(query).sort('created_at', -1))
    today = datetime.utcnow().date().isoformat()
    max_date = (datetime.utcnow().date() + timedelta(days=30)).isoformat()
    logger.debug(f"Retrieved {len(cars)} available vehicles")
    return render_template('view-cars.html', cars=cars, search_params=search_params, today=today, max_date=max_date)

# Car details
@app.route('/car_details/<car_id>')
def car_details(car_id):
    try:
        car = cars_collection.find_one({'_id': ObjectId(car_id)})
        if not car:
            flash('Vehicle not found', 'danger')
            return render_template('view-cars.html')
        logger.debug(f"Retrieved details for vehicle: {car_id}")
        return render_template('car-details.html', car=car)
    except Exception as e:
        logger.error(f"Error fetching car details: {str(e)}")
        flash('An error occurred while fetching vehicle details', 'danger')
        return render_template('view-cars.html')

# Book vehicle
@app.route('/book_car/<car_id>', methods=['GET', 'POST'])
def book_car(car_id):
    if 'firebase_uid' not in session:
        flash('Please login to book vehicles', 'danger')
        return redirect(url_for('login'))

    car = cars_collection.find_one({'_id': ObjectId(car_id)})
    if not car:
        flash('Vehicle not found', 'danger')
        return redirect(url_for('view_cars'))

    if not car.get('available', False):
        flash('This vehicle is not available for booking', 'danger')
        return redirect(url_for('view_cars'))

    search_params = session.get('search_params', {})
    today = datetime.utcnow().date().isoformat()
    max_date = (datetime.utcnow().date() + timedelta(days=30)).isoformat()

    # Validate search parameters before proceeding
    if not all([search_params.get('location'), search_params.get('start_date'), search_params.get('end_date'), search_params.get('vehicle_type')]):
        flash('Please select location, vehicle type, and dates before booking.', 'danger')
        return redirect(url_for('view_cars'))

    if request.method == 'POST':
        try:
            mobile = request.form['mobile']
            terms = request.form.get('terms')
            location = request.form['location'].strip()
            location_address = request.form['location_address'].strip()
            start_date_str = request.form['start_date']
            end_date_str = request.form['end_date']
            showroom = request.form.get('showroom', 'Default Showroom')

            if not terms:
                flash('You must agree to the Terms & Conditions.', 'danger')
                return render_template('book-car.html', car=car, today=today, max_date=max_date, search_params=search_params)
            
            if not re.match(r'^\d{10}$', mobile):
                flash('Mobile number must be 10 digits.', 'danger')
                return render_template('book-car.html', car=car, today=today, max_date=max_date, search_params=search_params)

            if not all([location, location_address, start_date_str, end_date_str]):
                flash('Please select a location and dates by searching first.', 'danger')
                return render_template('book-car.html', car=car, today=today, max_date=max_date, search_params=search_params)

            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            today = datetime.utcnow().date()
            max_date = today + timedelta(days=30)

            if start_date.year > 9999 or end_date.year > 9999:
                flash('Year cannot exceed 4 digits.', 'danger')
                return render_template('book-car.html', car=car, today=today, max_date=max_date, search_params=search_params)
            if start_date < today:
                flash('Start date cannot be in the past', 'danger')
                return render_template('book-car.html', car=car, today=today, max_date=max_date, search_params=search_params)
            if start_date >= end_date:
                flash('End date must be after start date', 'danger')
                return render_template('book-car.html', car=car, today=today, max_date=max_date, search_params=search_params)
            if start_date > max_date or end_date > max_date:
                flash('Dates must be within 1 month from today.', 'danger')
                return render_template('book-car.html', car=car, today=today, max_date=max_date, search_params=search_params)

            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.min.time())

            conflict = bookings_collection.find_one({
                'vehicle_id': ObjectId(car_id),
                'status': {'$ne': 'cancelled'},
                '$or': [
                    {'start_date': {'$lte': end_dt}, 'end_date': {'$gte': start_dt}}
                ]
            })

            if conflict:
                flash('Vehicle is already booked for the selected dates', 'danger')
                return render_template('book-car.html', car=car, today=today, max_date=max_date, search_params=search_params)

            total_price = (end_date - start_date).days * car['price_per_day']

            session['booking_data'] = {
                'vehicle_id': car_id,
                'start_date': start_date_str,
                'end_date': end_date_str,
                'location': location,
                'location_address': location_address,
                'mobile': mobile,
                'total_price': total_price,
                'showroom': showroom
            }
            logger.info(f"Booking data stored in session for vehicle: {car_id}")
            return redirect(url_for('payment', car_id=car_id))

        except ValueError as e:
            flash('Invalid date format (use YYYY-MM-DD)', 'danger')
            logger.error(f"ValueError in booking: {str(e)}")
            return render_template('book-car.html', car=car, today=today, max_date=max_date, search_params=search_params)
        except Exception as e:
            logger.error(f"Error booking vehicle: {str(e)}")
            flash('An error occurred while booking the vehicle', 'danger')
            return render_template('book-car.html', car=car, today=today, max_date=max_date, search_params=search_params)

    return render_template('book-car.html', car=car, today=today, max_date=max_date, search_params=search_params)

# Payment route
@app.route('/payment/<car_id>', methods=['GET', 'POST'])
def payment(car_id):
    if 'firebase_uid' not in session:
        flash('Please login to make payments', 'danger')
        return redirect(url_for('login'))

    car = cars_collection.find_one({'_id': ObjectId(car_id)})
    if not car:
        flash('Vehicle not found', 'danger')
        return redirect(url_for('view_cars'))

    booking_data = session.get('booking_data')
    if not booking_data or booking_data['vehicle_id'] != car_id:
        flash('Invalid booking data. Please try booking again.', 'danger')
        return redirect(url_for('book_car', car_id=car_id))

    if request.method == 'GET':
        try:
            order_data = {
                'amount': int(booking_data['total_price'] * 100),
                'currency': 'INR',
                'payment_capture': 1
            }
            order = razorpay_client.order.create(data=order_data)
            logger.info(f"Razorpay order created: {order['id']} for vehicle: {car_id}")
            return render_template('payment.html',
                                  car=car,
                                  booking_data=booking_data,
                                  order_id=order['id'],
                                  razorpay_key_id=RAZORPAY_KEY_ID,
                                  user={'email': session.get('username', 'Unknown')})
        except Exception as e:
            logger.error(f"Error creating Razorpay order: {str(e)}")
            flash('An error occurred while initiating payment.', 'danger')
            return redirect(url_for('book_car', car_id=car_id))

    return redirect(url_for('view_cars'))

# Verify payment
@app.route('/verify_payment', methods=['POST'])
def verify_payment():
    if 'firebase_uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    try:
        data = request.get_json()
        logger.debug(f"Payment verification data: {data}")
        params_dict = {
            'razorpay_order_id': data['razorpay_order_id'],
            'razorpay_payment_id': data['razorpay_payment_id'],
            'razorpay_signature': data['razorpay_signature']
        }

        razorpay_client.utility.verify_payment_signature(params_dict)

        car_id = data['car_id']
        booking_data = session.get('booking_data')
        logger.debug(f"Session booking_data: {booking_data}")
        if not booking_data or booking_data['vehicle_id'] != car_id:
            logger.warning(f"Invalid booking data for vehicle: {car_id}")
            return jsonify({'status': 'error', 'message': 'Invalid booking data'}), 400

        start_date = datetime.strptime(booking_data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(booking_data['end_date'], '%Y-%m-%d').date()

        vehicle = cars_collection.find_one({'_id': ObjectId(car_id)})
        logger.debug(f"Vehicle lookup result: {vehicle}")
        if not vehicle:
            logger.warning(f"Vehicle not found for car_id: {car_id}")
            return jsonify({'status': 'error', 'message': 'Vehicle not found'}), 400

        showroom = booking_data.get('showroom', booking_data['location'])

        booking = {
            'vehicle_id': ObjectId(car_id),
            'firebase_uid': session['firebase_uid'],
            'start_date': datetime.combine(start_date, datetime.min.time()),
            'end_date': datetime.combine(end_date, datetime.min.time()),
            'location': booking_data['location'],
            'location_address': booking_data['location_address'],
            'mobile': booking_data['mobile'],
            'showroom': showroom,
            'status': 'confirmed',
            'created_at': datetime.utcnow(),
            'total_price': booking_data['total_price'],
            'razorpay_order_id': data['razorpay_order_id'],
            'razorpay_payment_id': data['razorpay_payment_id']
        }
        booking_id = bookings_collection.insert_one(booking).inserted_id
        logger.debug(f"Booking saved with ID: {booking_id}")

        create_notification(
            firebase_uid=session['firebase_uid'],
            action='booking',
            message=f"You booked {vehicle['car_name']} from {start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')} at {showroom} on {datetime.now(IST).strftime('%d-%m-%Y at %H:%M:%S')}.",
            additional_data={
                'car_name': vehicle['car_name'],
                'start_date': booking_data['start_date'],
                'end_date': booking_data['end_date'],
                'showroom': showroom,
                'total_price': booking_data['total_price']
            }
        )

        # Clear booking_data and search_params after successful booking
        session.pop('booking_data', None)
        session.pop('search_params', None)

        logger.info(f"Booking confirmed for vehicle: {car_id} by Firebase UID: {session['firebase_uid']}")
        flash(f"Vehicle {vehicle['car_name']} booked successfully!", 'success')
        return jsonify({'status': 'success', 'redirect': url_for('view_cars')})
    except razorpay.errors.SignatureVerificationError as e:
        logger.error(f"Payment signature verification failed: {str(e)}")
        flash('Payment verification failed', 'danger')
        return jsonify({'status': 'error', 'message': 'Payment verification failed'}), 400
    except Exception as e:
        logger.error(f"Error verifying payment: {str(e)}")
        flash('An error occurred during payment verification', 'danger')
        return jsonify({'status': 'error', 'message': 'An error occurred during payment verification'}), 500

# Cancel booking
@app.route('/cancel_booking/<booking_id>', methods=['GET', 'POST'])
def cancel_booking(booking_id):
    if 'firebase_uid' not in session:
        flash('Please login to cancel bookings', 'danger')
        return redirect(url_for('login'))

    booking = bookings_collection.find_one({'_id': ObjectId(booking_id), 'firebase_uid': session['firebase_uid']})
    if not booking:
        flash('Booking not found or you do not have permission to cancel it', 'danger')
        return redirect(url_for('booking_history'))

    vehicle = cars_collection.find_one({'_id': booking['vehicle_id']})
    if not vehicle:
        flash('Vehicle details not found for this booking', 'danger')
        return redirect(url_for('booking_history'))

    if request.method == 'POST':
        try:
            bookings_collection.update_one(
                {'_id': ObjectId(booking_id)},
                {'$set': {'status': 'cancelled', 'updated_at': datetime.utcnow()}}
            )
            create_notification(
                firebase_uid=session['firebase_uid'],
                action='booking_cancelled',
                message=f"You cancelled your booking for {vehicle['car_name']} on {datetime.now(IST).strftime('%d-%m-%Y at %H:%M:%S')}.",
                additional_data={'car_name': vehicle['car_name'], 'booking_id': str(booking_id)}
            )
            flash('Booking cancelled successfully', 'success')
            return redirect(url_for('booking_history'))
        except Exception as e:
            logger.error(f"Error cancelling booking: {str(e)}")
            flash('An error occurred while cancelling the booking', 'danger')
            return render_template('cancel-booking.html', booking=booking, vehicle=vehicle)

    return render_template('cancel-booking.html', booking=booking, vehicle=vehicle)

# Get vehicle image
@app.route('/get_image/<car_id>')
def get_image(car_id):
    try:
        car = cars_collection.find_one({'_id': ObjectId(car_id)})
        if car and 'image_data' in car:
            return app.response_class(car['image_data'], mimetype='image/jpeg')
        logger.warning(f"No image found for vehicle: {car_id}")
        return 'No image found', 404
    except Exception as e:
        logger.error(f"Error fetching image: {str(e)}")
        return 'Error fetching image', 500

# Static pages
@app.route('/about')
def about():
    logger.debug("Accessing about page")
    return render_template('about.html')

@app.route('/contact')
def contact():
    logger.debug("Accessing contact page")
    return render_template('contact.html')

@app.route('/terms')
def terms():
    logger.debug("Accessing terms page")
    return render_template('terms.html')

# Error handler for 404
@app.errorhandler(404)
def page_not_found(e):
    logger.error(f"404 error: {request.url}")
    try:
        return render_template('404.html'), 404
    except Exception as e:
        logger.error(f"Error rendering 404.html: {str(e)}")
        return '<h1>404 - Page Not Found</h1><p>The requested page does not exist.</p>', 404

if __name__ == '__main__':
    app.run(debug=True)