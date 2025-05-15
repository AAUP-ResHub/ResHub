# ResHub Project

## Setup Instructions

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize the database:
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

4. Run the development server:
```bash
flask run
```

## Project Structure
- `app.py`: Main application file
- `models.py`: Database models (User and Role)
- `requirements.txt`: Project dependencies
- `render.yaml`: Render.com deployment configuration

## Deployment
The project is configured for deployment on Render.com. The deployment is automated when pushing to the main branch.