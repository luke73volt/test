from flask import Flask, render_template, request, redirect, url_for, g
import sqlite3
import matplotlib.pyplot as plt
import io
import base64
from collections import Counter
import click
from flask.cli import with_appcontext

app = Flask(__name__)
DATABASE_PATH = 'survey_results.db' # Default database path

# Database utility functions
def get_db():
    db_path = app.config.get('DATABASE', DATABASE_PATH)
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context(): # Ensure we are in an app context
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.cli.command('init-db')
@with_appcontext
def init_db_command():
    """Initializes the database."""
    init_db()
    click.echo('Initialized the database.')

# Ensure table exists (optional, init-db command is preferred)
# init_db()

@app.route('/')
def index():
    return render_template('survey.html')

@app.route('/submit', methods=['POST'])
def submit():
    if request.method == 'POST':
        satisfaction = request.form['satisfaction']
        feedback = request.form['feedback']

        db = get_db()
        db.execute('INSERT INTO results (satisfaction, feedback) VALUES (?, ?)',
                     (satisfaction, feedback))
        db.commit()
        # No need to close db here, teardown_appcontext handles it

        return redirect(url_for('results'))

@app.route('/results')
def results():
    db = get_db()
    db_results = db.execute('SELECT * FROM results').fetchall()
    # No need to close db here, teardown_appcontext handles it

    chart_url = None
    if db_results:
        # Process data for chart
        satisfaction_scores = [row['satisfaction'] for row in db_results]
        if satisfaction_scores:
            score_counts = Counter(satisfaction_scores)

            # Ensure all scores from 1 to 5 are present for the chart
            scores = list(range(1, 6))
            counts = [score_counts.get(score, 0) for score in scores]

            # Generate plot
            # Ensure Matplotlib uses 'Agg' backend when generating plots in a non-GUI environment
            # This is important if not already set globally for the process
            current_backend = plt.get_backend()
            try:
                plt.switch_backend('Agg')
                plt.figure(figsize=(8, 5))
                plt.bar(scores, counts, color=['red', 'lightcoral', 'lightyellow', 'lightgreen', 'green'])
                plt.xlabel("Satisfaction Score")
                plt.ylabel("Number of Responses")
                plt.title("Satisfaction Score Distribution")
                plt.xticks(scores)
                if counts: # Ensure counts is not empty before calling max()
                    plt.yticks(range(0, max(counts) + 1))
                else:
                    plt.yticks(range(0,1)) # Default y-ticks if no counts
                plt.tight_layout()

                # Save chart to a BytesIO object
                img = io.BytesIO()
                plt.savefig(img, format='png')
                img.seek(0)
                chart_url = base64.b64encode(img.getvalue()).decode()
            finally:
                plt.close() # Close the plot to free memory
                # Optionally switch back to original backend if necessary, though for server usually not.
                if current_backend != 'agg': # 'agg' is the lowercase version of 'Agg'
                    plt.switch_backend(current_backend)


    return render_template('results.html', results=db_results, chart_url=chart_url)

if __name__ == '__main__':
    app.config['DATABASE'] = DATABASE_PATH # Default for running the app
    # It's better to run 'flask init-db' manually than calling init_db() directly on app start
    # This gives more control, especially in production.
    # init_db() # Optional: if you want DB created/reset on every app start during dev

    # Ensure Matplotlib uses 'Agg' backend when running the development server
    # This prevents Matplotlib from trying to open a GUI window.
    plt.switch_backend('Agg')
    app.run(debug=True)
