# Receita Federal Payment Portal

## Overview
This Flask-based web application simulates a Brazilian Federal Revenue Service (Receita Federal) portal for tax payment regularization. Its primary purpose is to retrieve customer data, generate PIX payment requests via an integrated payment API, and process these payments. The project aims to provide a streamlined, user-friendly interface for tax payment, integrating with essential external services for lead data and payment processing.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### UI/UX Decisions
- **Template Engine**: Jinja2
- **CSS Framework**: Tailwind CSS (CDN) for responsive design
- **Icons**: Font Awesome 5.15.3
- **Custom Fonts**: Rawline font family for branding
- **JavaScript**: Vanilla JavaScript for dynamic elements like countdown timers and form interactions.
- **Design Approach**: Focus on dynamic content rendering based on customer data and responsive design for mobile compatibility, including urgent messaging for payment urgency.

### Technical Implementations
- **Backend Framework**: Flask (Python) for web application.
- **Session Management**: Flask sessions utilizing environment-based secret keys for security.
- **Logging**: Python's built-in logging for debugging and operational insights.
- **HTTP Client**: `requests` library for external API communication.
- **Customer Data Flow**: UTM parameters capture customer phone numbers, which are used for external API lookups to retrieve customer data (name, CPF), then stored in sessions.
- **Payment Processing**: Customer data validation, payment request creation via the integrated payment API, and generation of PIX payments with QR codes and payment links.
- **PIX Integration**: Implementation includes a fallback system to ensure authentic PIX generation, utilizing real customer data from CPF lookups for transactions and generating genuine QR codes. Transaction IDs are unique, and PIX codes are validated.
- **Deployment Strategy**: Designed for Gunicorn WSGI server in production, with environment variable configuration and HTTPS recommended for security. Supports Heroku deployment with Python 3.11 and uv package manager.
- **Error Handling**: Comprehensive logging for payment processing errors, graceful fallback for missing customer data, and input validation for payment requests.
- **Security**: Environment variables are used for sensitive credentials (e.g., `SESSION_SECRET`, `FOR4PAYMENTS_SECRET_KEY`, `MEDIUS_PAG_SECRET_KEY`, `MEDIUS_PAG_COMPANY_ID`) to avoid hardcoding.

### Feature Specifications
- **Customer Identification**: Handles UTM parameters to identify customers and retrieve their information from an external lead database.
- **Payment Generation**: Creates PIX payment requests.
- **Dynamic Content**: Displays dynamic content based on retrieved customer data and incorporates features like countdown timers for payment urgency.
- **Webhook Integration**: Includes a webhook endpoint for receiving payment status notifications.
- **Payment Status Checking**: Provides a route to check the status of a payment.
- **Notification Integration**: Sends notifications for successful transactions via Pushcut.

## External Dependencies

### APIs
- **Lead Database API**: `https://api-lista-leads.replit.app/api/search/{phone}`
- **For4Payments API**: `https://app.for4payments.com.br/api/v1` (Note: This API was previously used, but the system evolved to use MEDIUS PAG).
- **MEDIUS PAG API**: Used for authentic PIX generation and transaction management.
- **Pushcut API**: Used for sending notifications for successful transactions.

### CDN Resources
- **Tailwind CSS**: `https://cdn.tailwindcss.com`
- **Font Awesome**: `https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css`

### Environment Variables
- `SESSION_SECRET`: Flask session encryption key.
- `FOR4PAYMENTS_SECRET_KEY`: API authentication token for For4Payments (if still in use for any fallback).
- `MEDIUS_PAG_SECRET_KEY`: Secret key for MEDIUS PAG API authentication.
- `MEDIUS_PAG_COMPANY_ID`: Company ID for MEDIUS PAG API.

## Recent Changes

- August 05, 2025: ✅ **Multi-Year Debt Values Updated** - Valores específicos por ano:
  * 2019: R$ 41,54
  * 2020: R$ 47,47  
  * 2021: R$ 49,41
  * Total mantido em R$ 138,42
  * Interface atualizada com valores diferenciados por exercício fiscal