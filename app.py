import flask
from flask import url_for, redirect, request, render_template
from flask_login import LoginManager

app = flask.Flask(__name__)
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/join/<code>')
def join(code):

@app.route('/<code>/time')
def time(code):
    return render_template('time.html')

@app.route('/<code>/location')
def location(code):
    return render_template('location.html')

@app.route('/<code>/ingredient')
def ingredient(code):
    return render_template('ingredient.html')

@app.route('/<code>/spice')
def spice():
    return render_template('spice.html')

@app.route('/<code>/waiting')
def waiting():
    return render_template('waiting.html')

@app.route('/<code>/results')
def results():
    return render_template('results.html')

if __name__ == '__main__':
    app.run()

