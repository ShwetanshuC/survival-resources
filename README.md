# Food Bank Project

A Django web application for survival/food bank resources.

## Setup

### Prerequisites
- Python 3.9+

### Installation

```bash
# Clone the repository
git clone https://github.com/ShwetanshuC/survival-resources.git
cd survival-resources

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install Django==4.2.29 requests==2.32.5 overpassify==1.2.3
```

### Run the development server

```bash
python manage.py migrate
python manage.py runserver
```
