# ResHub - Research Collaboration Platform

ResHub is a comprehensive web platform designed for researchers to share papers, discuss ideas, and collaborate on academic projects.

## Features

### User Management
- User registration and authentication
- Profile management
- Role-based access control

### Paper Management
- Upload and share research papers
- Search papers by keywords
- Track paper metrics (views, downloads)
- User-specific paper collections

### Forum System
- Create and participate in topic discussions
- Markdown support for rich text formatting
- User post management (edit, delete)
- Admin capabilities (pin posts, moderate content)

## Technology Stack

- **Backend**: Flask (Python web framework)
- **Database**: SQLAlchemy ORM with SQLite
- **Authentication**: Flask-Login
- **Frontend**: Bootstrap 5, HTML, CSS, JavaScript
- **Markdown Processing**: markdown-it-py, Bleach (for XSS protection)

## Setup and Installation

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/ResHub.git
   cd ResHub
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Initialize the database:
   ```
   flask db upgrade
   ```

5. Run the application:
   ```
   flask run
   ```

6. Access the application at http://127.0.0.1:5000

## Project Structure

```
ResHub/
├── app/                    # Application package
│   ├── auth/               # Authentication blueprint
│   ├── errors/             # Error handling
│   ├── forum/              # Forum subsystem
│   ├── paper/              # Paper management
│   ├── static/             # Static files (CSS, JS, images)
│   │   ├── uploads/        # User uploads (papers, etc.)
│   ├── templates/          # HTML templates
│   ├── __init__.py         # Application factory
│   ├── config.py           # Configuration
│   ├── extensions.py       # Flask extensions
│   ├── models.py           # Database models
│   └── routes.py           # Main routes
├── migrations/             # Database migrations
├── .gitignore              # Git ignore file
├── requirements.txt        # Project dependencies
└── README.md               # Project documentation
```

## Development

### Adding New Features

1. Create a new branch for your feature
2. Implement your changes
3. Write tests for your feature
4. Submit a pull request

### Database Migrations

After making changes to models, run:

```
flask db migrate -m "Description of changes"
flask db upgrade
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.