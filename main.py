from flask import Flask, render_template, request, flash, redirect, send_from_directory
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ThisIsASecret'
app.config['MONGO_URI'] = 'mongodb://localhost:27017/wad'
mongo = PyMongo(app)
socketio = SocketIO(app)

# ------------------------------  HOME PAGE ------------------------------

@app.route('/')
def home_page():
    return render_template('index.html')

# ------------------------------  AUTHENTICATION ------------------------------

# SignUp feature
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    # Render SignUp page on GET request
    if request.method == 'GET':
        return render_template('auth/signup.html')
    
    # Handle SingUp data on POST request
    else:
        # Get username and password from form data
        username = request.form.get('username')
        password = request.form.get('password')

        # Check if username is already used
        if mongo.db.users.count_documents({'username':username}) != 0:
            flash('Username exists!')
            return redirect('/signup')
        
        # Otherwise sign up new user
        else:
            # Save username and password hash
            mongo.db.users.insert_one({
                'username': username,
                'password': generate_password_hash(password)
            })
            # Send flash message and redirect user to authentication page
            flash('Signed up!')
            return redirect('/auth')

# Authentication feature
@app.route('/auth', methods=['GET', 'POST'])
def auth():
    # Render Authentication page on GET request
    if request.method == 'GET':
        return render_template('auth/auth.html')
    
    # Handle log in data on POST request
    else:
        # Get username and password from form data
        username = request.form.get('username')
        password = request.form.get('password')

        # Find user in database
        user = mongo.db.users.find_one({'username': username})

        # Check log in credentials
        if user and check_password_hash(user['password'], password):
            # Render secret page if success
            return render_template('auth/secret.html')
        else:
            # Send flash message and render authentication page if fail
            flash('Username or password is not correct!')
            return render_template('auth/auth.html')

# ------------------------------  UPLOAD IMAGE ------------------------------

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Check if file name is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Image upload feature
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    # Render upload page on GET request
    if request.method == 'GET':
        return render_template('upload/upload.html')
    
    # Handle upload data on POST request
    else:
        # Check if there is a image file in post data
        if 'image' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        # Get file data
        file = request.files['image']
        
        # Check the file
        if not file or file.filename == '':
            flash('No selected file')
            return redirect(request.url)
            
        # Check filename extension
        if not allowed_file(file.filename):
            flash('Invalid file extension')
            return redirect(request.url)
        
        # Save uploaded file to 'upload' folder
        filename = secure_filename(file.filename)
        file.save(os.path.join('upload', filename))

        # Redirect user to uploaded image
        return redirect(f'/uploaded/{filename}')

# Serve uploaded images from folder 'upload'
@app.route('/uploaded/<path:filename>')
def uploaded(filename):
    return send_from_directory('upload', filename)

# ------------------------------  NOTEBOOK ------------------------------

# Handle notebook feature
@app.route('/notebook', methods=['GET', 'POST'])
def notebook():
    # Render page on GET request
    if request.method == 'GET':
        # handle if user set limit number of notes to be displayed
        number = request.args.get('number')
        if number and int(number) > 0:
            notes = list(mongo.db.notes.find({}).limit(int(number)))
            
            # Send flash message
            flash(f"Limit applied. Show {len(notes)} notes")
        
        # Otherwise display all notes in database 
        else:
            notes = list(mongo.db.notes.find({}))
        
        # Render notebook page with existing notes
        return render_template('notebook/notebook.html', notes=notes, number=len(notes))
    
    # Handle new note on POST request
    else:
        # Get title and content of the post
        title = request.form.get('title')
        content = request.form.get('note')

        # Save data to database
        mongo.db.notes.insert_one({
            'title': title,
            'content': content
        })

        # Flash message
        flash("New note added!")

        # Redirect user back to notebook page
        return redirect('/notebook')

        # Can also render notebook page right here without redirect
        # 
        # notes = list(mongo.db.notes.find({}))
        # return render_template('notebook/notebook.html', notes=notes)

# Clear all notes features
@app.route('/notebook/clear', methods=['POST'])
def clear_note():
    # Clear data in database
    mongo.db.notes.drop()

    # Redirect user back to notebook page
    return redirect('/notebook')

# ------------------------------  CHATBOT ------------------------------

# Page for chatting with bot
@app.route('/chatbot', methods=['GET'])
def chatbot():
    return render_template('chatbot/chat.html')

# Websocket on event 'connect':
@socketio.on('connect')
def on_connect():
    # Send back chat history to client
    history = list(mongo.db.chat.find({}))
    for mess in history:
        socketio.emit('update', {
            'user_name': mess['user_name'],
            'message': mess['message']
        })


# Websocket on event 'message' (message is sent by 'send' function)
@socketio.on('message')
def on_message(json_data, methods=['GET', 'POST']):
    # Send message back to user
    socketio.emit('update', json_data)

    # Save message to history
    mongo.db.chat.insert_one(json_data)

    # Generate response and send back to user
    resp = "OK"
    socketio.send(resp, to=request.sid)

    # Save bot's response to history
    mongo.db.chat.insert_one({
        'user_name': 'Bot',
        'message': resp
    })

# Websocket on event 'clear history'
@socketio.on('clear history')
def clear_history(mes, methods=['GET', 'POST']):
    # Clear all chat history in database
    mongo.db.chat.drop()

# ------------------------------  RUN ------------------------------
# ------------------------------  APP ------------------------------

if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True)