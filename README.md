# Rentigoooo - Car Rental System (User Side)

## Overview
Rentigoooo is a user-side web application for a car rental system built with Flask, Firebase, MongoDB, and Razorpay. It allows users to browse vehicles (cars, bikes, and scooters), book rentals, make payments, and manage their booking history. The application features secure user authentication, real-time vehicle search, and payment integration.

**Note**: This repository contains only the **user-side** code. The admin-side code is not included. For access to admin-side files or collaboration inquiries, please contact me at [your-email@example.com](mailto:your-email@example.com).

## Features
- **User Authentication**: Secure registration and login using Firebase Authentication with email and password.
- **Vehicle Search**: Search for available vehicles by location, vehicle type (car, bike, scooty), and rental dates.
- **Booking System**: Book vehicles with date validation to prevent conflicts.
- **Payment Integration**: Process payments securely using Razorpay.
- **Booking History**: View and cancel bookings with notification support.
- **Notifications**: Receive real-time notifications for actions like login, registration, booking confirmations, and cancellations.
- **Responsive Design**: User-friendly interface with templates for home, vehicle details, booking, payment, and more.

## Tech Stack
- **Backend**: Flask (Flask framework)
- **Authentication**: Firebase Authentication
- **Database**: MongoDB for storing user data, bookings, and vehicle details
- **Payment Gateway**: Razorpay
- **Environment Management**: Python `dotenv` for managing sensitive credentials
- **Other Libraries**: `pymongo`, `firebase-admin`, `pytz`, `razorpay`

## Prerequisites
- Python 3.8+
- MongoDB instance (local or MongoDB Atlas)
- Firebase project with Authentication enabled
- Razorpay account for payment integration
- Git and a GitHub account

## Installation
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/rentigoooo.git
   cd rentigoooo
