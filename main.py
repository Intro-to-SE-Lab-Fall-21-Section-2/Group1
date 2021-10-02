# Main application script

from flask import Flask, render_template, redirect

app = Flask(__name__)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/start")
def star():
    return render_template('startPage.html')

@app.route("/login")
def login():
    return render_template('loginpage.html')

@app.route("/register")
def register():
    return render_template('emailCreator.html')

@app.route("/inbox_list")
def inboxList():
    return render_template('inboxlist.html')

@app.route("/drafts_list")
def draftsList():
    return render_template('draftslist.html')

@app.route("/edit_window")
def editWindow():
    return render_template('editwindow.html')

@app.route("/inbox_read")
def inboxRead():
    return render_template('inboxread.html')

@app.route("/outbox_list")
def outboxList():
    return render_template('outboxlist.html')

@app.route("/outbox_read")
def outboxRead():
    return render_template('outboxread.html')

@app.route("/signup")
def signUp():
    return render_template('signup.html')

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=80) 