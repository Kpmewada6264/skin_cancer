import re
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from tensorflow.keras.models import load_model
import numpy as np
import os
from PIL import Image
from .models import Prediction

# Load model
model_path = os.path.join(os.path.dirname(__file__), 'keras_model', 'kp_model.h5')
model = load_model(model_path)
classes = ['akiec', 'bcc', 'bkl', 'df', 'mel', 'nv', 'vasc']

# Password validation regex patterns
password_regex = {
    'length': r'.{8,}',  # at least 8 characters
    'alphabet': r'[a-zA-Z]',  # at least one letter
    'digit': r'\d',  # at least one digit
    'special': r'[!@#$%^&*(),.?":{}|<>]'  # at least one special character
}

def validate_password(password):
    errors = []
    if not re.search(password_regex['length'], password):
        errors.append("Password must be at least 8 characters.")
    if not re.search(password_regex['alphabet'], password):
        errors.append("Password must include at least one letter.")
    if not re.search(password_regex['digit'], password):
        errors.append("Password must include at least one number.")
    if not re.search(password_regex['special'], password):
        errors.append("Password must include at least one special character.")
    return errors

# ---------------- Home ----------------
def home(request):
    return render(request, 'myapp/home.html')

# ---------------- Register ----------------
def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm = request.POST.get('confirm')

        # Basic validation for empty fields
        if not username or not email or not password or not confirm:
            return render(request, 'myapp/register.html', {'error': 'All fields are required.'})
        
        # Passwords match?
        if password != confirm:
            return render(request, 'myapp/register.html', {'error': 'Passwords do not match.'})

        # Validate email format
        try:
            validate_email(email)
        except ValidationError:
            return render(request, 'myapp/register.html', {'error': 'Enter a valid email address.'})

        # Check username uniqueness
        if User.objects.filter(username=username).exists():
            return render(request, 'myapp/register.html', {'error': 'Username already exists.'})

        # Check email uniqueness
        if User.objects.filter(email=email).exists():
            return render(request, 'myapp/register.html', {'error': 'Email already registered.'})

        # Password strength validation
        pwd_errors = validate_password(password)
        if pwd_errors:
            return render(request, 'myapp/register.html', {'error': ' '.join(pwd_errors)})

        # Create user
        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()
        return redirect('login')

    return render(request, 'myapp/register.html')

# ---------------- Login ----------------
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not username or not password:
            return render(request, 'myapp/login.html', {'error': 'All fields are required.'})

        # Optional: check if username exists before authenticate to give clearer error
        if not User.objects.filter(username=username).exists():
            return render(request, 'myapp/login.html', {'error': 'Username does not exist.'})

        # You can add password validation here as well if needed (not typical for login)

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('predict')
        else:
            return render(request, 'myapp/login.html', {'error': 'Invalid credentials'})

    return render(request, 'myapp/login.html')

# ---------------- Logout ----------------
def logout_view(request):
    logout(request)
    return redirect('home')

# ---------------- Predict ----------------
@login_required
def predict_view(request):
    result_label = None
    prediction_instance = None
    error = None  # add error variable

    if request.method == 'POST':
        name = request.POST.get('name')
        age = request.POST.get('age')
        gender = request.POST.get('gender')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        address = request.POST.get('address')
        img_file = request.FILES.get('image')

        # Manual validation
        if not all([name, age, gender, phone, email, address, img_file]):
            error = 'All fields are required.'
        else:
            try:
                age = int(age)
            except ValueError:
                error = 'Age must be a number.'

            if not error:
                if not phone.isdigit() or len(phone) < 10:
                    error = 'Enter a valid phone number.'

            if not error:
                try:
                    validate_email(email)
                except ValidationError:
                    error = 'Enter a valid email address.'

        if not error:
            # Prepare image
            file_path = default_storage.save('temp.jpg', img_file)
            img = Image.open(default_storage.path(file_path)).convert('RGB')
            img = img.resize((128, 128))
            img_array = np.array(img).astype(np.float32).reshape(1, 128, 128, 3)

            # Predict
            prediction = model.predict(img_array)
            result_index = np.argmax(prediction)
            result_label = classes[result_index]

            # Save to database
            prediction_instance = Prediction.objects.create(
                user=request.user,
                name=name,
                age=age,
                gender=gender,
                phone=phone,
                email=email,
                address=address,
                image=img_file,
                result=result_label
            )
        # If error, result_label and prediction_instance remain None

    return render(request, 'myapp/predict.html', {
        'result': result_label,
        'prediction': prediction_instance,
        'error': error,
    })
