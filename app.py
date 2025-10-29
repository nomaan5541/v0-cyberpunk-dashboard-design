from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database/school_management.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Create database directory if it doesn't exist
os.makedirs('database', exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ============ ROLE-BASED ACCESS CONTROL DECORATOR ============

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != role:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ============ DATABASE MODELS ============

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # super_admin, school_admin, teacher, student
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class School(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'))
    roll_number = db.Column(db.String(50))
    class_name = db.Column(db.String(50))
    date_of_birth = db.Column(db.Date)
    parent_phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'))
    subject = db.Column(db.String(100))
    qualification = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # present, absent, late, excused
    remarks = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Fee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'))
    amount = db.Column(db.Float, nullable=False)
    fee_type = db.Column(db.String(100), nullable=False)  # tuition, transport, etc.
    due_date = db.Column(db.Date, nullable=False)
    paid_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='pending')  # pending, paid, overdue
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'))
    class_name = db.Column(db.String(50), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AssignmentSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    submission_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending')  # pending, submitted, graded
    grade = db.Column(db.Float)
    feedback = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ============ AUTHENTICATION ROUTES ============

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    if current_user.is_authenticated:
        if current_user.role == 'super_admin':
            return redirect(url_for('super_admin_dashboard'))
        elif current_user.role == 'school_admin':
            return redirect(url_for('school_admin_dashboard'))
        elif current_user.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        else:
            return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not email or not password:
            return jsonify({'error': 'Missing required fields'}), 400
        
        if password != confirm_password:
            return jsonify({'error': 'Passwords do not match'}), 400
        
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        user = User(username=username, email=email, role='student')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        return jsonify({'message': 'Registration successful'}), 201
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            login_user(user)
            return redirect(url_for('dashboard'))
        
        return jsonify({'error': 'Invalid username or password'}), 401
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

# ============ DATABASE INITIALIZATION ============

@app.route('/init-db', methods=['POST'])
def init_db():
    """Initialize database with tables and create super admin"""
    db.create_all()
    
    # Create super admin if doesn't exist
    if not User.query.filter_by(role='super_admin').first():
        super_admin = User(
            username='superadmin',
            email='admin@school.com',
            role='super_admin',
            is_active=True
        )
        super_admin.set_password('admin123')
        db.session.add(super_admin)
        db.session.commit()
        return jsonify({'message': 'Database initialized and super admin created'}), 201
    
    return jsonify({'message': 'Database already initialized'}), 200

# ============ SUPER ADMIN ROUTES ============

@app.route('/super-admin/dashboard')
@login_required
@role_required('super_admin')
def super_admin_dashboard():
    total_schools = School.query.count()
    total_admins = User.query.filter_by(role='school_admin').count()
    total_students = Student.query.count()
    total_teachers = Teacher.query.count()
    
    schools = School.query.all()
    
    stats = {
        'total_schools': total_schools,
        'total_admins': total_admins,
        'total_students': total_students,
        'total_teachers': total_teachers
    }
    
    return render_template('super_admin_dashboard.html', stats=stats, schools=schools)

@app.route('/super-admin/schools', methods=['GET', 'POST'])
@login_required
@role_required('super_admin')
def manage_schools():
    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        phone = request.form.get('phone')
        email = request.form.get('email')
        admin_username = request.form.get('admin_username')
        admin_email = request.form.get('admin_email')
        admin_password = request.form.get('admin_password')
        
        if not all([name, admin_username, admin_email, admin_password]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Create school admin user
        if User.query.filter_by(username=admin_username).first():
            return jsonify({'error': 'Admin username already exists'}), 400
        
        admin_user = User(
            username=admin_username,
            email=admin_email,
            role='school_admin',
            is_active=True
        )
        admin_user.set_password(admin_password)
        db.session.add(admin_user)
        db.session.flush()
        
        # Create school
        school = School(
            name=name,
            address=address,
            phone=phone,
            email=email,
            admin_id=admin_user.id,
            is_active=True
        )
        db.session.add(school)
        db.session.commit()
        
        return jsonify({'message': 'School created successfully', 'school_id': school.id}), 201
    
    schools = School.query.all()
    return render_template('manage_schools.html', schools=schools)

@app.route('/super-admin/schools/<int:school_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@role_required('super_admin')
def school_detail(school_id):
    school = School.query.get_or_404(school_id)
    
    if request.method == 'GET':
        admin = User.query.get(school.admin_id)
        return jsonify({
            'id': school.id,
            'name': school.name,
            'address': school.address,
            'phone': school.phone,
            'email': school.email,
            'admin': admin.username if admin else None,
            'is_active': school.is_active,
            'created_at': school.created_at.isoformat()
        })
    
    elif request.method == 'PUT':
        data = request.get_json()
        school.name = data.get('name', school.name)
        school.address = data.get('address', school.address)
        school.phone = data.get('phone', school.phone)
        school.email = data.get('email', school.email)
        school.is_active = data.get('is_active', school.is_active)
        db.session.commit()
        return jsonify({'message': 'School updated successfully'})
    
    elif request.method == 'DELETE':
        db.session.delete(school)
        db.session.commit()
        return jsonify({'message': 'School deleted successfully'})

@app.route('/super-admin/admins')
@login_required
@role_required('super_admin')
def manage_admins():
    admins = User.query.filter_by(role='school_admin').all()
    admin_data = []
    
    for admin in admins:
        school = School.query.filter_by(admin_id=admin.id).first()
        admin_data.append({
            'id': admin.id,
            'username': admin.username,
            'email': admin.email,
            'school': school.name if school else 'No School',
            'is_active': admin.is_active,
            'created_at': admin.created_at
        })
    
    return render_template('manage_admins.html', admins=admin_data)

@app.route('/super-admin/admins/<int:admin_id>/toggle', methods=['POST'])
@login_required
@role_required('super_admin')
def toggle_admin_status(admin_id):
    admin = User.query.get_or_404(admin_id)
    admin.is_active = not admin.is_active
    db.session.commit()
    return jsonify({'message': 'Admin status updated', 'is_active': admin.is_active})

# ============ SCHOOL ADMIN ROUTES ============

@app.route('/school-admin/setup', methods=['GET', 'POST'])
@login_required
@role_required('school_admin')
def school_admin_setup():
    """Setup wizard for school admin to configure their school"""
    school = School.query.filter_by(admin_id=current_user.id).first()
    
    if request.method == 'POST':
        step = request.form.get('step')
        
        if step == '1':
            # Update school basic info
            school.name = request.form.get('name')
            school.address = request.form.get('address')
            school.phone = request.form.get('phone')
            school.email = request.form.get('email')
            db.session.commit()
            return jsonify({'message': 'Step 1 completed', 'next_step': 2}), 200
        
        elif step == '2':
            # Add classes/sections
            classes = request.form.getlist('classes[]')
            # Store in session or database
            return jsonify({'message': 'Step 2 completed', 'next_step': 3}), 200
        
        elif step == '3':
            # Invite teachers
            teacher_emails = request.form.getlist('teacher_emails[]')
            for email in teacher_emails:
                # Create teacher user and send invitation
                pass
            return jsonify({'message': 'Setup completed!', 'next_step': 'complete'}), 200
    
    if not school:
        return redirect(url_for('dashboard'))
    
    return render_template('school_admin_setup.html', school=school)

@app.route('/school-admin/dashboard')
@login_required
@role_required('school_admin')
def school_admin_dashboard():
    """School admin dashboard"""
    school = School.query.filter_by(admin_id=current_user.id).first()
    
    if not school:
        return redirect(url_for('dashboard'))
    
    total_students = Student.query.filter_by(school_id=school.id).count()
    total_teachers = Teacher.query.filter_by(school_id=school.id).count()
    total_classes = db.session.query(Student.class_name).filter_by(school_id=school.id).distinct().count()
    
    stats = {
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_classes': total_classes
    }
    
    recent_students = Student.query.filter_by(school_id=school.id).order_by(Student.created_at.desc()).limit(5).all()
    recent_teachers = Teacher.query.filter_by(school_id=school.id).order_by(Teacher.created_at.desc()).limit(5).all()
    
    return render_template('school_admin_dashboard.html', 
                         school=school, 
                         stats=stats, 
                         recent_students=recent_students,
                         recent_teachers=recent_teachers)

@app.route('/school-admin/settings', methods=['GET', 'POST'])
@login_required
@role_required('school_admin')
def school_admin_settings():
    """School admin settings"""
    school = School.query.filter_by(admin_id=current_user.id).first()
    
    if not school:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        school.name = request.form.get('name', school.name)
        school.address = request.form.get('address', school.address)
        school.phone = request.form.get('phone', school.phone)
        school.email = request.form.get('email', school.email)
        db.session.commit()
        return jsonify({'message': 'Settings updated successfully'}), 200
    
    return render_template('school_admin_settings.html', school=school)

# ============ STUDENT MANAGEMENT ROUTES ============

@app.route('/school-admin/students', methods=['GET', 'POST'])
@login_required
@role_required('school_admin')
def manage_students():
    """Manage students for the school"""
    school = School.query.filter_by(admin_id=current_user.id).first()
    
    if not school:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # Create new student
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        roll_number = request.form.get('roll_number')
        class_name = request.form.get('class_name')
        date_of_birth = request.form.get('date_of_birth')
        parent_phone = request.form.get('parent_phone')
        password = request.form.get('password')
        
        if not all([first_name, last_name, email, roll_number, class_name]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        # Create student user
        username = f"{first_name.lower()}.{last_name.lower()}"
        if User.query.filter_by(username=username).first():
            username = f"{first_name.lower()}.{last_name.lower()}.{school.id}"
        
        student_user = User(
            username=username,
            email=email,
            role='student',
            is_active=True
        )
        student_user.set_password(password or 'student123')
        db.session.add(student_user)
        db.session.flush()
        
        # Create student record
        student = Student(
            user_id=student_user.id,
            school_id=school.id,
            roll_number=roll_number,
            class_name=class_name,
            date_of_birth=date_of_birth,
            parent_phone=parent_phone
        )
        db.session.add(student)
        db.session.commit()
        
        return jsonify({'message': 'Student added successfully', 'student_id': student.id}), 201
    
    # Get all students for this school
    students = Student.query.filter_by(school_id=school.id).all()
    student_data = []
    
    for student in students:
        user = User.query.get(student.user_id)
        student_data.append({
            'id': student.id,
            'name': f"{user.username}",
            'email': user.email,
            'roll_number': student.roll_number,
            'class_name': student.class_name,
            'date_of_birth': student.date_of_birth,
            'parent_phone': student.parent_phone,
            'created_at': student.created_at
        })
    
    return render_template('manage_students.html', students=student_data)

@app.route('/school-admin/students/<int:student_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@role_required('school_admin')
def student_detail(student_id):
    """Get, update, or delete a student"""
    school = School.query.filter_by(admin_id=current_user.id).first()
    student = Student.query.get_or_404(student_id)
    
    # Verify student belongs to this school
    if student.school_id != school.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if request.method == 'GET':
        user = User.query.get(student.user_id)
        return jsonify({
            'id': student.id,
            'name': user.username,
            'email': user.email,
            'roll_number': student.roll_number,
            'class_name': student.class_name,
            'date_of_birth': str(student.date_of_birth) if student.date_of_birth else None,
            'parent_phone': student.parent_phone,
            'created_at': student.created_at.isoformat()
        })
    
    elif request.method == 'PUT':
        data = request.get_json()
        student.roll_number = data.get('roll_number', student.roll_number)
        student.class_name = data.get('class_name', student.class_name)
        student.date_of_birth = data.get('date_of_birth', student.date_of_birth)
        student.parent_phone = data.get('parent_phone', student.parent_phone)
        db.session.commit()
        return jsonify({'message': 'Student updated successfully'})
    
    elif request.method == 'DELETE':
        user = User.query.get(student.user_id)
        db.session.delete(student)
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'Student deleted successfully'})

@app.route('/school-admin/students/class/<class_name>')
@login_required
@role_required('school_admin')
def get_class_students(class_name):
    """Get all students in a specific class"""
    school = School.query.filter_by(admin_id=current_user.id).first()
    students = Student.query.filter_by(school_id=school.id, class_name=class_name).all()
    
    student_data = []
    for student in students:
        user = User.query.get(student.user_id)
        student_data.append({
            'id': student.id,
            'name': user.username,
            'roll_number': student.roll_number,
            'email': user.email
        })
    
    return jsonify(student_data)

@app.route('/school-admin/students/bulk-import', methods=['POST'])
@login_required
@role_required('school_admin')
def bulk_import_students():
    """Bulk import students from CSV"""
    school = School.query.filter_by(admin_id=current_user.id).first()
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Only CSV files are supported'}), 400
    
    try:
        import csv
        import io
        
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_data = csv.DictReader(stream)
        
        imported_count = 0
        errors = []
        
        for row in csv_data:
            try:
                first_name = row.get('first_name', '').strip()
                last_name = row.get('last_name', '').strip()
                email = row.get('email', '').strip()
                roll_number = row.get('roll_number', '').strip()
                class_name = row.get('class_name', '').strip()
                
                if not all([first_name, last_name, email, roll_number, class_name]):
                    errors.append(f"Row {imported_count + 1}: Missing required fields")
                    continue
                
                if User.query.filter_by(email=email).first():
                    errors.append(f"Row {imported_count + 1}: Email already exists")
                    continue
                
                username = f"{first_name.lower()}.{last_name.lower()}"
                if User.query.filter_by(username=username).first():
                    username = f"{first_name.lower()}.{last_name.lower()}.{school.id}"
                
                student_user = User(
                    username=username,
                    email=email,
                    role='student',
                    is_active=True
                )
                student_user.set_password('student123')
                db.session.add(student_user)
                db.session.flush()
                
                student = Student(
                    user_id=student_user.id,
                    school_id=school.id,
                    roll_number=roll_number,
                    class_name=class_name,
                    date_of_birth=row.get('date_of_birth'),
                    parent_phone=row.get('parent_phone')
                )
                db.session.add(student)
                imported_count += 1
            
            except Exception as e:
                errors.append(f"Row {imported_count + 1}: {str(e)}")
        
        db.session.commit()
        return jsonify({
            'message': f'Successfully imported {imported_count} students',
            'imported': imported_count,
            'errors': errors
        }), 201
    
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 400

# ============ ATTENDANCE MANAGEMENT ROUTES ============

@app.route('/school-admin/attendance', methods=['GET', 'POST'])
@login_required
@role_required('school_admin')
def manage_attendance():
    """Manage student attendance"""
    school = School.query.filter_by(admin_id=current_user.id).first()
    
    if not school:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        date = request.form.get('date')
        class_name = request.form.get('class_name')
        attendance_data = request.form.getlist('attendance[]')
        
        if not date or not class_name:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Get all students in the class
        students = Student.query.filter_by(school_id=school.id, class_name=class_name).all()
        
        for idx, student in enumerate(students):
            status = attendance_data[idx] if idx < len(attendance_data) else 'absent'
            
            # Check if attendance already exists for this date
            existing = Attendance.query.filter_by(
                student_id=student.id,
                date=date
            ).first()
            
            if existing:
                existing.status = status
            else:
                attendance = Attendance(
                    student_id=student.id,
                    date=date,
                    status=status
                )
                db.session.add(attendance)
        
        db.session.commit()
        return jsonify({'message': 'Attendance recorded successfully'}), 201
    
    # Get unique classes
    classes = db.session.query(Student.class_name).filter_by(school_id=school.id).distinct().all()
    classes = [c[0] for c in classes]
    
    return render_template('manage_attendance.html', classes=classes)

@app.route('/school-admin/attendance/class/<class_name>/<date>')
@login_required
@role_required('school_admin')
def get_class_attendance(class_name, date):
    """Get attendance for a specific class on a specific date"""
    school = School.query.filter_by(admin_id=current_user.id).first()
    students = Student.query.filter_by(school_id=school.id, class_name=class_name).all()
    
    attendance_data = []
    for student in students:
        user = User.query.get(student.user_id)
        attendance = Attendance.query.filter_by(
            student_id=student.id,
            date=date
        ).first()
        
        attendance_data.append({
            'student_id': student.id,
            'name': user.username,
            'roll_number': student.roll_number,
            'status': attendance.status if attendance else 'absent'
        })
    
    return jsonify(attendance_data)

@app.route('/school-admin/attendance/report')
@login_required
@role_required('school_admin')
def attendance_report():
    """Generate attendance report"""
    school = School.query.filter_by(admin_id=current_user.id).first()
    
    if not school:
        return redirect(url_for('dashboard'))
    
    class_name = request.args.get('class_name')
    month = request.args.get('month')
    
    if not class_name or not month:
        classes = db.session.query(Student.class_name).filter_by(school_id=school.id).distinct().all()
        classes = [c[0] for c in classes]
        return render_template('attendance_report.html', classes=classes)
    
    # Get attendance data for the month
    students = Student.query.filter_by(school_id=school.id, class_name=class_name).all()
    
    report_data = []
    for student in students:
        user = User.query.get(student.user_id)
        
        # Count attendance by status for the month
        attendances = Attendance.query.filter_by(student_id=student.id).all()
        
        present_count = sum(1 for a in attendances if a.status == 'present')
        absent_count = sum(1 for a in attendances if a.status == 'absent')
        late_count = sum(1 for a in attendances if a.status == 'late')
        total_days = len(attendances)
        
        percentage = (present_count / total_days * 100) if total_days > 0 else 0
        
        report_data.append({
            'name': user.username,
            'roll_number': student.roll_number,
            'present': present_count,
            'absent': absent_count,
            'late': late_count,
            'total': total_days,
            'percentage': round(percentage, 2)
        })
    
    return render_template('attendance_report.html', 
                         report_data=report_data, 
                         class_name=class_name,
                         month=month)

# ============ FEE MANAGEMENT ROUTES ============

@app.route('/school-admin/fees', methods=['GET', 'POST'])
@login_required
@role_required('school_admin')
def manage_fees():
    """Manage student fees"""
    school = School.query.filter_by(admin_id=current_user.id).first()
    
    if not school:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        amount = request.form.get('amount')
        fee_type = request.form.get('fee_type')
        due_date = request.form.get('due_date')
        
        if not all([student_id, amount, fee_type, due_date]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        fee = Fee(
            student_id=student_id,
            school_id=school.id,
            amount=float(amount),
            fee_type=fee_type,
            due_date=due_date,
            status='pending'
        )
        db.session.add(fee)
        db.session.commit()
        
        return jsonify({'message': 'Fee added successfully', 'fee_id': fee.id}), 201
    
    # Get all students
    students = Student.query.filter_by(school_id=school.id).all()
    student_data = []
    
    for student in students:
        user = User.query.get(student.user_id)
        student_data.append({
            'id': student.id,
            'name': user.username,
            'email': user.email,
            'class': student.class_name
        })
    
    return render_template('manage_fees.html', students=student_data)

@app.route('/school-admin/fees/student/<int:student_id>')
@login_required
@role_required('school_admin')
def student_fees(student_id):
    """Get all fees for a student"""
    school = School.query.filter_by(admin_id=current_user.id).first()
    student = Student.query.get_or_404(student_id)
    
    # Verify student belongs to this school
    if student.school_id != school.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    fees = Fee.query.filter_by(student_id=student_id).all()
    
    fee_data = []
    total_pending = 0
    total_paid = 0
    
    for fee in fees:
        fee_data.append({
            'id': fee.id,
            'fee_type': fee.fee_type,
            'amount': fee.amount,
            'due_date': str(fee.due_date),
            'paid_date': str(fee.paid_date) if fee.paid_date else None,
            'status': fee.status
        })
        
        if fee.status == 'pending' or fee.status == 'overdue':
            total_pending += fee.amount
        elif fee.status == 'paid':
            total_paid += fee.amount
    
    return jsonify({
        'fees': fee_data,
        'total_pending': total_pending,
        'total_paid': total_paid
    })

@app.route('/school-admin/fees/<int:fee_id>/mark-paid', methods=['POST'])
@login_required
@role_required('school_admin')
def mark_fee_paid(fee_id):
    """Mark a fee as paid"""
    school = School.query.filter_by(admin_id=current_user.id).first()
    fee = Fee.query.get_or_404(fee_id)
    
    # Verify fee belongs to this school
    if fee.school_id != school.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    fee.status = 'paid'
    fee.paid_date = datetime.utcnow().date()
    db.session.commit()
    
    return jsonify({'message': 'Fee marked as paid'})

@app.route('/school-admin/fees/report')
@login_required
@role_required('school_admin')
def fees_report():
    """Generate fees report"""
    school = School.query.filter_by(admin_id=current_user.id).first()
    
    if not school:
        return redirect(url_for('dashboard'))
    
    class_name = request.args.get('class_name')
    
    if not class_name:
        classes = db.session.query(Student.class_name).filter_by(school_id=school.id).distinct().all()
        classes = [c[0] for c in classes]
        return render_template('fees_report.html', classes=classes)
    
    # Get all students in the class
    students = Student.query.filter_by(school_id=school.id, class_name=class_name).all()
    
    report_data = []
    total_pending = 0
    total_paid = 0
    
    for student in students:
        user = User.query.get(student.user_id)
        fees = Fee.query.filter_by(student_id=student.id).all()
        
        pending = sum(f.amount for f in fees if f.status in ['pending', 'overdue'])
        paid = sum(f.amount for f in fees if f.status == 'paid')
        
        total_pending += pending
        total_paid += paid
        
        report_data.append({
            'name': user.username,
            'roll_number': student.roll_number,
            'email': user.email,
            'pending': pending,
            'paid': paid,
            'total': pending + paid
        })
    
    return render_template('fees_report.html',
                         report_data=report_data,
                         class_name=class_name,
                         total_pending=total_pending,
                         total_paid=total_paid)

# ============ TEACHER MANAGEMENT ROUTES ============

@app.route('/school-admin/teachers', methods=['GET', 'POST'])
@login_required
@role_required('school_admin')
def manage_teachers():
    """Manage teachers for the school"""
    school = School.query.filter_by(admin_id=current_user.id).first()
    
    if not school:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        qualification = request.form.get('qualification')
        password = request.form.get('password')
        
        if not all([first_name, last_name, email, subject]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        username = f"{first_name.lower()}.{last_name.lower()}"
        if User.query.filter_by(username=username).first():
            username = f"{first_name.lower()}.{last_name.lower()}.{school.id}"
        
        teacher_user = User(
            username=username,
            email=email,
            role='teacher',
            is_active=True
        )
        teacher_user.set_password(password or 'teacher123')
        db.session.add(teacher_user)
        db.session.flush()
        
        teacher = Teacher(
            user_id=teacher_user.id,
            school_id=school.id,
            subject=subject,
            qualification=qualification
        )
        db.session.add(teacher)
        db.session.commit()
        
        return jsonify({'message': 'Teacher added successfully', 'teacher_id': teacher.id}), 201
    
    teachers = Teacher.query.filter_by(school_id=school.id).all()
    teacher_data = []
    
    for teacher in teachers:
        user = User.query.get(teacher.user_id)
        teacher_data.append({
            'id': teacher.id,
            'name': user.username,
            'email': user.email,
            'subject': teacher.subject,
            'qualification': teacher.qualification,
            'created_at': teacher.created_at
        })
    
    return render_template('manage_teachers.html', teachers=teacher_data)

@app.route('/school-admin/teachers/<int:teacher_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@role_required('school_admin')
def teacher_detail(teacher_id):
    """Get, update, or delete a teacher"""
    school = School.query.filter_by(admin_id=current_user.id).first()
    teacher = Teacher.query.get_or_404(teacher_id)
    
    if teacher.school_id != school.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if request.method == 'GET':
        user = User.query.get(teacher.user_id)
        return jsonify({
            'id': teacher.id,
            'name': user.username,
            'email': user.email,
            'subject': teacher.subject,
            'qualification': teacher.qualification,
            'created_at': teacher.created_at.isoformat()
        })
    
    elif request.method == 'PUT':
        data = request.get_json()
        teacher.subject = data.get('subject', teacher.subject)
        teacher.qualification = data.get('qualification', teacher.qualification)
        db.session.commit()
        return jsonify({'message': 'Teacher updated successfully'})
    
    elif request.method == 'DELETE':
        user = User.query.get(teacher.user_id)
        db.session.delete(teacher)
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'Teacher deleted successfully'})

# ============ TEACHER DASHBOARD ROUTES ============

@app.route('/teacher/dashboard')
@login_required
@role_required('teacher')
def teacher_dashboard():
    """Teacher dashboard"""
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    
    if not teacher:
        return redirect(url_for('dashboard'))
    
    # Get statistics
    total_assignments = Assignment.query.filter_by(teacher_id=teacher.id).count()
    total_classes = db.session.query(Assignment.class_name).filter_by(teacher_id=teacher.id).distinct().count()
    
    # Get pending submissions
    pending_submissions = db.session.query(AssignmentSubmission).join(
        Assignment, AssignmentSubmission.assignment_id == Assignment.id
    ).filter(
        Assignment.teacher_id == teacher.id,
        AssignmentSubmission.status == 'submitted'
    ).count()
    
    # Get recent assignments
    recent_assignments = Assignment.query.filter_by(teacher_id=teacher.id).order_by(
        Assignment.created_at.desc()
    ).limit(5).all()
    
    stats = {
        'total_assignments': total_assignments,
        'total_classes': total_classes,
        'pending_submissions': pending_submissions
    }
    
    return render_template('teacher_dashboard.html', 
                         teacher=teacher, 
                         stats=stats,
                         recent_assignments=recent_assignments)

# ============ ASSIGNMENT MANAGEMENT ROUTES ============

@app.route('/teacher/assignments', methods=['GET', 'POST'])
@login_required
@role_required('teacher')
def manage_assignments():
    """Manage assignments"""
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    
    if not teacher:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        class_name = request.form.get('class_name')
        title = request.form.get('title')
        description = request.form.get('description')
        due_date = request.form.get('due_date')
        
        if not all([class_name, title, due_date]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        assignment = Assignment(
            teacher_id=teacher.id,
            class_name=class_name,
            subject=teacher.subject,
            title=title,
            description=description,
            due_date=due_date
        )
        db.session.add(assignment)
        db.session.commit()
        
        return jsonify({'message': 'Assignment created successfully', 'assignment_id': assignment.id}), 201
    
    assignments = Assignment.query.filter_by(teacher_id=teacher.id).all()
    assignment_data = []
    
    for assignment in assignments:
        submissions = AssignmentSubmission.query.filter_by(assignment_id=assignment.id).all()
        submitted_count = sum(1 for s in submissions if s.status in ['submitted', 'graded'])
        
        assignment_data.append({
            'id': assignment.id,
            'title': assignment.title,
            'class_name': assignment.class_name,
            'due_date': str(assignment.due_date),
            'submissions': len(submissions),
            'submitted': submitted_count,
            'created_at': assignment.created_at
        })
    
    return render_template('manage_assignments.html', assignments=assignment_data)

@app.route('/teacher/assignments/<int:assignment_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@role_required('teacher')
def assignment_detail(assignment_id):
    """Get, update, or delete an assignment"""
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    assignment = Assignment.query.get_or_404(assignment_id)
    
    if assignment.teacher_id != teacher.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if request.method == 'GET':
        submissions = AssignmentSubmission.query.filter_by(assignment_id=assignment_id).all()
        submission_data = []
        
        for submission in submissions:
            student = Student.query.get(submission.student_id)
            user = User.query.get(student.user_id)
            submission_data.append({
                'id': submission.id,
                'student_name': user.username,
                'status': submission.status,
                'grade': submission.grade,
                'submission_date': str(submission.submission_date) if submission.submission_date else None
            })
        
        return jsonify({
            'id': assignment.id,
            'title': assignment.title,
            'description': assignment.description,
            'class_name': assignment.class_name,
            'due_date': str(assignment.due_date),
            'submissions': submission_data,
            'created_at': assignment.created_at.isoformat()
        })
    
    elif request.method == 'PUT':
        data = request.get_json()
        assignment.title = data.get('title', assignment.title)
        assignment.description = data.get('description', assignment.description)
        assignment.due_date = data.get('due_date', assignment.due_date)
        db.session.commit()
        return jsonify({'message': 'Assignment updated successfully'})
    
    elif request.method == 'DELETE':
        AssignmentSubmission.query.filter_by(assignment_id=assignment_id).delete()
        db.session.delete(assignment)
        db.session.commit()
        return jsonify({'message': 'Assignment deleted successfully'})

@app.route('/teacher/assignments/<int:assignment_id>/submissions')
@login_required
@role_required('teacher')
def assignment_submissions(assignment_id):
    """Get all submissions for an assignment"""
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    assignment = Assignment.query.get_or_404(assignment_id)
    
    if assignment.teacher_id != teacher.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    submissions = AssignmentSubmission.query.filter_by(assignment_id=assignment_id).all()
    submission_data = []
    
    for submission in submissions:
        student = Student.query.get(submission.student_id)
        user = User.query.get(student.user_id)
        submission_data.append({
            'id': submission.id,
            'student_id': student.id,
            'student_name': user.username,
            'roll_number': student.roll_number,
            'status': submission.status,
            'grade': submission.grade,
            'feedback': submission.feedback,
            'submission_date': str(submission.submission_date) if submission.submission_date else None
        })
    
    return jsonify(submission_data)

@app.route('/teacher/assignments/<int:assignment_id>/submissions/<int:submission_id>/grade', methods=['POST'])
@login_required
@role_required('teacher')
def grade_submission(assignment_id, submission_id):
    """Grade a student submission"""
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    assignment = Assignment.query.get_or_404(assignment_id)
    submission = AssignmentSubmission.query.get_or_404(submission_id)
    
    if assignment.teacher_id != teacher.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    submission.grade = data.get('grade')
    submission.feedback = data.get('feedback')
    submission.status = 'graded'
    db.session.commit()
    
    return jsonify({'message': 'Submission graded successfully'})

# ============ TEACHER REPORTS ROUTES ============

@app.route('/teacher/reports/class-performance')
@login_required
@role_required('teacher')
def class_performance_report():
    """Generate class performance report"""
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    
    if not teacher:
        return redirect(url_for('dashboard'))
    
    class_name = request.args.get('class_name')
    
    if not class_name:
        classes = db.session.query(Assignment.class_name).filter_by(
            teacher_id=teacher.id
        ).distinct().all()
        classes = [c[0] for c in classes]
        return render_template('class_performance_report.html', classes=classes)
    
    # Get all students in the class
    school = School.query.get(teacher.school_id)
    students = Student.query.filter_by(school_id=school.id, class_name=class_name).all()
    
    report_data = []
    
    for student in students:
        user = User.query.get(student.user_id)
        
        # Get all submissions for this student
        submissions = db.session.query(AssignmentSubmission).join(
            Assignment, AssignmentSubmission.assignment_id == Assignment.id
        ).filter(
            AssignmentSubmission.student_id == student.id,
            Assignment.teacher_id == teacher.id
        ).all()
        
        grades = [s.grade for s in submissions if s.grade is not None]
        average_grade = sum(grades) / len(grades) if grades else 0
        submitted_count = sum(1 for s in submissions if s.status in ['submitted', 'graded'])
        
        report_data.append({
            'name': user.username,
            'roll_number': student.roll_number,
            'total_assignments': len(submissions),
            'submitted': submitted_count,
            'average_grade': round(average_grade, 2),
            'status': 'Excellent' if average_grade >= 80 else 'Good' if average_grade >= 60 else 'Needs Improvement'
        })
    
    return render_template('class_performance_report.html',
                         report_data=report_data,
                         class_name=class_name)

@app.route('/teacher/reports/attendance')
@login_required
@role_required('teacher')
def teacher_attendance_report():
    """Generate attendance report for teacher's classes"""
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    
    if not teacher:
        return redirect(url_for('dashboard'))
    
    class_name = request.args.get('class_name')
    
    if not class_name:
        school = School.query.get(teacher.school_id)
        classes = db.session.query(Student.class_name).filter_by(
            school_id=school.id
        ).distinct().all()
        classes = [c[0] for c in classes]
        return render_template('teacher_attendance_report.html', classes=classes)
    
    # Get all students in the class
    school = School.query.get(teacher.school_id)
    students = Student.query.filter_by(school_id=school.id, class_name=class_name).all()
    
    report_data = []
    
    for student in students:
        user = User.query.get(student.user_id)
        attendances = Attendance.query.filter_by(student_id=student.id).all()
        
        present_count = sum(1 for a in attendances if a.status == 'present')
        absent_count = sum(1 for a in attendances if a.status == 'absent')
        late_count = sum(1 for a in attendances if a.status == 'late')
        total_days = len(attendances)
        
        percentage = (present_count / total_days * 100) if total_days > 0 else 0
        
        report_data.append({
            'name': user.username,
            'roll_number': student.roll_number,
            'present': present_count,
            'absent': absent_count,
            'late': late_count,
            'total': total_days,
            'percentage': round(percentage, 2)
        })
    
    return render_template('teacher_attendance_report.html',
                         report_data=report_data,
                         class_name=class_name)

@app.route('/teacher/reports/summary')
@login_required
@role_required('teacher')
def teacher_summary_report():
    """Generate overall summary report for teacher"""
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    
    if not teacher:
        return redirect(url_for('dashboard'))
    
    # Get all assignments
    assignments = Assignment.query.filter_by(teacher_id=teacher.id).all()
    
    # Get all submissions
    submissions = db.session.query(AssignmentSubmission).join(
        Assignment, AssignmentSubmission.assignment_id == Assignment.id
    ).filter(Assignment.teacher_id == teacher.id).all()
    
    # Calculate statistics
    total_assignments = len(assignments)
    total_submissions = len(submissions)
    graded_submissions = sum(1 for s in submissions if s.status == 'graded')
    pending_submissions = sum(1 for s in submissions if s.status == 'submitted')
    
    grades = [s.grade for s in submissions if s.grade is not None]
    average_grade = sum(grades) / len(grades) if grades else 0
    
    # Get class-wise breakdown
    class_breakdown = {}
    for assignment in assignments:
        if assignment.class_name not in class_breakdown:
            class_breakdown[assignment.class_name] = {
                'assignments': 0,
                'submissions': 0,
                'graded': 0
            }
        class_breakdown[assignment.class_name]['assignments'] += 1
        
        class_submissions = [s for s in submissions if s.assignment_id == assignment.id]
        class_breakdown[assignment.class_name]['submissions'] += len(class_submissions)
        class_breakdown[assignment.class_name]['graded'] += sum(1 for s in class_submissions if s.status == 'graded')
    
    summary = {
        'total_assignments': total_assignments,
        'total_submissions': total_submissions,
        'graded_submissions': graded_submissions,
        'pending_submissions': pending_submissions,
        'average_grade': round(average_grade, 2),
        'class_breakdown': class_breakdown
    }
    
    return render_template('teacher_summary_report.html', summary=summary)

if __name__ == '__main__':
    app.run(debug=True)
