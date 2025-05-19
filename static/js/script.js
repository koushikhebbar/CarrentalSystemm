// Import Firebase SDK modules
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import { getAuth, signInWithEmailAndPassword, verifyPasswordResetCode, confirmPasswordReset, sendPasswordResetEmail } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

// Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyBTJu-bUbu-LMAu6fQLOwkFnGia_gfsyiI",
  authDomain: "rentigoooo.firebaseapp.com",
  projectId: "rentigoooo",
  storageBucket: "rentigoooo.firebasestorage.app",
  messagingSenderId: "530661940745",
  appId: "1:530661940745:web:2f4e79809fab335435e2d8",
  measurementId: "G-MGLZC6TT7S"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// Toggle mobile menu
function toggleMenu() {
    const menu = document.getElementById('mobile-menu');
    if (menu) {
        menu.classList.toggle('hidden');
    }
}

// Fetch notifications
async function fetchNotifications() {
    try {
        const response = await fetch('/get_notifications');
        const data = await response.json();
        if (data.status === 'success') {
            const notificationList = document.getElementById('notification-list');
            const unreadCount = document.getElementById('unread-count');
            
            // Update unread count
            if (data.unread_count > 0) {
                unreadCount.textContent = data.unread_count;
                unreadCount.classList.remove('hidden');
            } else {
                unreadCount.classList.add('hidden');
            }

            // Clear existing notifications
            notificationList.innerHTML = '';

            // Populate notifications
            if (data.notifications.length > 0) {
                data.notifications.forEach(notification => {
                    const div = document.createElement('div');
                    div.className = `flex items-start p-2 rounded ${notification.read ? '' : 'bg-blue-50'}`;
                    div.innerHTML = `
                        <i class="fas ${
                            notification.action === 'login' ? 'fa-sign-in-alt' :
                            notification.action === 'logout' ? 'fa-sign-out-alt' :
                            notification.action === 'register' ? 'fa-user-plus' :
                            notification.action === 'booking' ? 'fa-car' :
                            notification.action === 'booking_cancelled' ? 'fa-times-circle' :
                            notification.action === 'password_reset_request' ? 'fa-key' :
                            notification.action === 'password_reset_success' ? 'fa-check-circle' :
                            notification.action === 'add_vehicle' ? 'fa-car' : 'fa-info-circle'
                        } text-[#FF6B00] text-lg mr-3"></i>
                        <div>
                            <p class="text-gray-800 text-sm">${notification.message}</p>
                            <p class="text-gray-500 text-xs">${notification.timestamp}</p>
                        </div>
                    `;
                    notificationList.appendChild(div);
                });
            } else {
                notificationList.innerHTML = '<p class="text-gray-500 text-sm text-center">No notifications yet.</p>';
            }
        } else {
            console.error('Failed to fetch notifications:', data.message);
            document.getElementById('notification-list').innerHTML = '<p class="text-gray-500 text-sm text-center">Failed to load notifications.</p>';
        }
    } catch (error) {
        console.error('Error fetching notifications:', error);
        document.getElementById('notification-list').innerHTML = '<p class="text-gray-500 text-sm text-center">Error loading notifications.</p>';
    }
}

// Smooth scroll for anchor links and form handling
document.addEventListener('DOMContentLoaded', () => {
    // Smooth scroll
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({ behavior: 'smooth' });
            } else if (this.getAttribute('href') === '#home') {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
    });

    // Notification bell click handler
    const notificationBell = document.getElementById('notification-bell');
    const notificationPopup = document.getElementById('notification-popup');
    if (notificationBell && notificationPopup) {
        notificationBell.addEventListener('click', () => {
            notificationPopup.classList.toggle('hidden');
            if (!notificationPopup.classList.contains('hidden')) {
                fetchNotifications();
            }
        });

        // Close popup when clicking outside
        document.addEventListener('click', (e) => {
            if (!notificationBell.contains(e.target) && !notificationPopup.contains(e.target)) {
                notificationPopup.classList.add('hidden');
            }
        });

        // Fetch notifications on page load
        fetchNotifications();
    }

    // Login form handling
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            const errorMessageDiv = document.getElementById('error-message');

            // Client-side email validation
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email)) {
                errorMessageDiv.textContent = 'Please enter a valid email address.';
                errorMessageDiv.classList.remove('hidden');
                return;
            }

            // Clear previous error message
            errorMessageDiv.classList.add('hidden');

            try {
                const userCredential = await signInWithEmailAndPassword(auth, email, password);
                const idToken = await userCredential.user.getIdToken();
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ idToken })
                });
                const data = await response.json();
                if (data.status === 'success') {
                    window.location.href = data.redirect || '/view_cars';
                } else {
                    errorMessageDiv.textContent = data.message || 'Login failed. Please try again.';
                    errorMessageDiv.classList.remove('hidden');
                }
            } catch (error) {
                console.error('Login error:', error.message, error.stack);
                let errorMessage = 'An error occurred. Please try again.';
                switch (error.code) {
                    case 'auth/invalid-email':
                        errorMessage = 'Invalid email format.';
                        break;
                    case 'auth/user-not-found':
                        errorMessage = 'No account found with this email.';
                        break;
                    case 'auth/wrong-password':
                        errorMessage = 'Incorrect password.';
                        break;
                    case 'auth/too-many-requests':
                        errorMessage = 'Too many login attempts. Please try again later.';
                        break;
                    case 'auth/invalid-credential':
                        errorMessage = 'Invalid email or password.';
                        break;
                    case 'auth/network-request-failed':
                        errorMessage = 'Network error: Unable to connect to authentication service.';
                        break;
                    default:
                    errorMessage = 'Login failed: ' + error.message;
                }
                errorMessageDiv.textContent = errorMessage;
                errorMessageDiv.classList.remove('hidden');
            }
        });

        // Hide error message when user starts typing
        const inputs = document.querySelectorAll('#email, #password');
        inputs.forEach(input => {
            input.addEventListener('input', () => {
                document.getElementById('error-message').classList.add('hidden');
            });
        });
    }

    // Forgot password form handling
    const forgotPasswordForm = document.getElementById('forgot-password-form');
    if (forgotPasswordForm) {
        forgotPasswordForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('email').value;
            const errorMessageDiv = document.getElementById('error-message');

            // Client-side email validation
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email)) {
                errorMessageDiv.textContent = 'Please enter a valid email address.';
                errorMessageDiv.classList.remove('hidden');
                return;
            }

            try {
                await sendPasswordResetEmail(auth, email, {
                    url: 'https://rentigoooo.firebaseapp.com/reset_password',
                    handleCodeInApp: true
                });
                window.location.href = '/login';
            } catch (error) {
                console.error('Forgot password error:', error.message, error.stack);
                let errorMessage = 'An error occurred while sending the reset email.';
                switch (error.code) {
                    case 'auth/invalid-email':
                        errorMessage = 'Invalid email format.';
                        break;
                    case 'auth/user-not-found':
                        errorMessage = 'No account found with this email.';
                        break;
                    case 'auth/too-many-requests':
                        errorMessage = 'Too many requests. Please try again later.';
                        break;
                    default:
                        errorMessage = 'Failed to send reset email: ' + error.message;
                }
                errorMessageDiv.textContent = errorMessage;
                errorMessageDiv.classList.remove('hidden');
            }
        });
    }

    // Reset password form handling
    const resetPasswordForm = document.getElementById('reset-password-form');
    if (resetPasswordForm) {
        const urlParams = new URLSearchParams(window.location.search);
        const oobCode = urlParams.get('oobCode');
        
        if (!oobCode) {
            window.location.href = '/login';
            return;
        }

        verifyPasswordResetCode(auth, oobCode).then((email) => {
            resetPasswordForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const newPassword = document.getElementById('password').value;
                const errorMessageDiv = document.getElementById('error-message');

                // Basic password validation
                if (newPassword.length < 8) {
                    errorMessageDiv.textContent = 'Password must be at least 8 characters long.';
                    errorMessageDiv.classList.remove('hidden');
                    return;
                }

                try {
                    await confirmPasswordReset(auth, oobCode, newPassword);
                    const response = await fetch('/reset_password', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ email })
                    });
                    const data = await response.json();
                    if (data.status === 'success') {
                        window.location.href = '/login';
                    } else {
                        errorMessageDiv.textContent = data.message || 'Password reset failed. Please try again.';
                        errorMessageDiv.classList.remove('hidden');
                    }
                } catch (error) {
                    console.error('Password reset error:', error.message, error.stack);
                    let errorMessage = 'An error occurred during password reset.';
                    switch (error.code) {
                        case 'auth/invalid-action-code':
                            errorMessage = 'Invalid or expired reset code.';
                            break;
                        case 'auth/weak-password':
                            errorMessage = 'Password is too weak. Please choose a stronger password.';
                        break;
                        default:
                            errorMessage = 'Password reset failed: ' + error.message;
                    }
                    errorMessageDiv.textContent = errorMessage;
                    errorMessageDiv.classList.remove('hidden');
                }
            });
        }).catch((error) => {
            console.error('Verify reset code error:', error.message, error.stack);
            window.location.href = '/login';
        });
    }

    // Register form handling
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        const errorMessageDiv = document.getElementById('error-message');
        const inputs = document.querySelectorAll('#username, #email, #mobile, #password');

        // Validation functions
        const validateUsername = (username) => {
            const usernameRegex = /^[a-zA-Z0-9_]{3,20}$/;
            return usernameRegex.test(username);
        };

        const validateEmail = (email) => {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return emailRegex.test(email);
        };

        const validateMobile = (mobile) => {
            return /^\d{10}$/.test(mobile);
        };

        const validatePassword = (password) => {
            const length = password.length >= 8;
            const uppercase = /[A-Z]/.test(password);
            const lowercase = /[a-z]/.test(password);
            const number = /[0-9]/.test(password);
            const special = /[!@#$%^&*(),.?":{}|<>]/.test(password);
            return { length, uppercase, lowercase, number, special, valid: length && uppercase && lowercase && number && special };
        };

        // Real-time validation and label color update
        inputs.forEach(input => {
            input.addEventListener('input', () => {
                errorMessageDiv.classList.add('hidden');
                const label = input.parentElement.previousElementSibling;

                if (input.id === 'username') {
                    label.className = `block text-sm font-medium mb-2 transition-colors ${validateUsername(input.value) ? 'text-green-600' : 'text-[#0057A3]'}`;
                } else if (input.id === 'email') {
                    label.className = `block text-sm font-medium mb-2 transition-colors ${validateEmail(input.value) ? 'text-green-600' : 'text-[#0057A3]'}`;
                } else if (input.id === 'mobile') {
                    label.className = `block text-sm font-medium mb-2 transition-colors ${validateMobile(input.value) ? 'text-green-600' : 'text-[#0057A3]'}`;
                } else if (input.id === 'password') {
                    const { length, uppercase, lowercase, number, special } = validatePassword(input.value);
                    label.className = `block text-sm font-medium mb-2 transition-colors ${length && uppercase && lowercase && number && special ? 'text-green-600' : 'text-[#0057A3]'}`;
                    // Update password requirements with correct signs
                    document.getElementById('req-length').innerHTML = `<i class="fas ${length ? 'fa-check text-green-500' : 'fa-times text-red-500'} mr-2"></i> At least 8 characters`;
                    document.getElementById('req-uppercase').innerHTML = `<i class="fas ${uppercase ? 'fa-check text-green-500' : 'fa-times text-red-500'} mr-2"></i> One uppercase letter`;
                    document.getElementById('req-lowercase').innerHTML = `<i class="fas ${lowercase ? 'fa-check text-green-500' : 'fa-times text-red-500'} mr-2"></i> One lowercase letter`;
                    document.getElementById('req-number').innerHTML = `<i class="fas ${number ? 'fa-check text-green-500' : 'fa-times text-red-500'} mr-2"></i> One number`;
                    document.getElementById('req-special').innerHTML = `<i class="fas ${special ? 'fa-check text-green-500' : 'fa-times text-red-500'} mr-2"></i> One special character`;
                }
            });
        });

        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value.trim();
            const email = document.getElementById('email').value.trim();
            const mobile = document.getElementById('mobile').value.trim();
            const password = document.getElementById('password').value;

            // Client-side validation
            if (!validateUsername(username)) {
                errorMessageDiv.textContent = 'Username must be 3–20 characters and contain only letters, numbers, or underscores.';
                errorMessageDiv.classList.remove('hidden');
                document.querySelector('label[for="username"]').className = 'block text-sm font-medium text-red-600 mb-2 transition-colors';
                return;
            }
            if (!validateEmail(email)) {
                errorMessageDiv.textContent = 'Please enter a valid email address.';
                errorMessageDiv.classList.remove('hidden');
                document.querySelector('label[for="email"]').className = 'block text-sm font-medium text-red-600 mb-2 transition-colors';
                return;
            }
            if (!validateMobile(mobile)) {
                errorMessageDiv.textContent = 'Mobile number must be exactly 10 digits.';
                errorMessageDiv.classList.remove('hidden');
                document.querySelector('label[for="mobile"]').className = 'block text-sm font-medium text-red-600 mb-2 transition-colors';
                return;
            }
            if (!validatePassword(password).valid) {
                errorMessageDiv.textContent = 'Password does not meet all requirements.';
                errorMessageDiv.classList.remove('hidden');
                document.querySelector('label[for="password"]').className = 'block text-sm font-medium text-red-600 mb-2 transition-colors';
                return;
            }

            // Clear previous error message
            errorMessageDiv.classList.add('hidden');

            try {
                const formData = new FormData(registerForm);
                const response = await fetch('/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: new URLSearchParams(formData)
                });

                if (response.redirected) {
                    window.location.href = response.url;
                    return;
                }

                // Check if response is JSON
                const contentType = response.headers.get('content-type');
                let data;
                if (contentType && contentType.includes('application/json')) {
                    data = await response.json();
                } else {
                    const text = await response.text();
                    throw new SyntaxError(`Expected JSON but received: ${text}`);
                }

                if (data.status === 'success') {
                    window.location.href = data.redirect || '/login';
                } else {
                    errorMessageDiv.textContent = data.message || 'Registration failed. Please try again.';
                    errorMessageDiv.classList.remove('hidden');
                    if (data.message.includes('username')) {
                        document.querySelector('label[for="username"]').className = 'block text-sm font-medium text-red-600 mb-2 transition-colors';
                    } else if (data.message.includes('email')) {
                        document.querySelector('label[for="email"]').className = 'block text-sm font-medium text-red-600 mb-2 transition-colors';
                    }
                }
            } catch (error) {
                console.error('Registration error:', error.message, error.stack);
                let errorMessage = 'An error occurred during registration. Please try again.';
                if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
                    errorMessage = 'Network error: Unable to connect to the server. Please check your internet connection.';
                } else if (error.message.includes('Firebase')) {
                    errorMessage = 'Authentication service error. Please try again later.';
                } else if (error.name === 'SyntaxError') {
                    errorMessage = `Server response error: ${error.message}`;
                }
                errorMessageDiv.textContent = errorMessage;
                errorMessageDiv.classList.remove('hidden');
            }
        });
    }
});