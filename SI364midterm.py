###############################
####### SETUP (OVERALL) #######
###############################

## Import statements
# Import statements
import os
from flask import Flask, render_template, session, redirect, url_for, flash, request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, ValidationError # Note that you may need to import more here! Check out examples that do what you want to figure out what.
from wtforms.validators import Required, Length # Here, too
from flask_sqlalchemy import SQLAlchemy
import requests
import json

## App setup code
app = Flask(__name__)
app.debug = True
app.use_reloader = True
app.config['SECRET_KEY'] = 'hard to guess string from si364'

## All app.config values
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://localhost/shellar364midterm"
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

## Statements for db setup (and manager setup if using Manager)
db = SQLAlchemy(app)


######################################
######## HELPER FXNS (If any) ########
######################################




##################
##### MODELS #####
##################

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer,primary_key=True)
    user = db.Column(db.String(64))
    username = db.Column(db.String(64))

    def __repr__(self):
        return "{}".format(self.user)

class Song(db.Model):
    __tablename__ = "songs"
    id = db.Column(db.Integer,primary_key=True)
    songname = db.Column(db.String(150))
    artistid = db.Column(db.Integer, db.ForeignKey('artists.id'))

    def __repr__(self):
        return "Song Title: {}".format(self.songname)

class Artist(db.Model):
    __tablename__ = "artists"
    id = db.Column(db.Integer,primary_key=True)
    artistname = db.Column(db.String(150))
    songs = db.relationship('Song', backref='Artist')

    def __repr__(self):
        "{} (Artist ID: {})".format(self.artistname, self.id)

class Suggested(db.Model):
    __tablename__ = "suggested"
    id = db.Column(db.Integer,primary_key=True)
    songname = db.Column(db.String(150))
    artistname = db.Column(db.String(150))
    rating = db.Column(db.String(64))

    def __repr__(self):
        return "Song: {} -- Artist: {} -- Description: {}".format(self.songname, self.artistname, self.rating)

###################
###### FORMS ######
###################

class UserForm(FlaskForm):
    user = StringField("Please enter your name (Must start with a letter).",validators=[Required()])
    def validate_user(self, field):
        numbers = ['0','1','2','3','4','5','6','7','8','9']
        if field.data[0] in numbers:
            raise ValidationError('Name started with number, try again!')
    username = StringField("Please enter your username.",validators=[Required()])
    access_token = StringField("Please enter your user access token from 'https://developer.spotify.com/web-api/console/get-recently-played/' With Relevant Scope 'user-read-recently-played': ")
    submit = SubmitField()

class ArtistForm(FlaskForm):
    artist = StringField("Please enter artist's name to display which of their songs have been listened to by users.",validators=[Required()])
    submit = SubmitField()

class SuggestionForm(FlaskForm):
    songname = StringField("Please enter a song you wish to suggest.",validators=[Required()])
    artistname = StringField("Please enter the artist of the song you referred.",validators=[Required()])
    rating = StringField("Please enter a short description of why you suggested this song.",validators=[Required()])
    submit = SubmitField()

#######################
###### VIEW FXNS ######
#######################
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.route('/', methods=['GET', 'POST'])
def home():
    form = UserForm() # User should be able to enter name after name and each one will be saved, even if it's a duplicate! Sends data with GET
    if form.validate_on_submit():
        user = form.user.data
        username = form.username.data
        current_user = User.query.filter_by(user=user).first()
        if not current_user:
            current_user = User(user=user, username=username)
            db.session.add(current_user)
            db.session.commit()

        spotify_url = 'https://api.spotify.com/v1/me/player/recently-played'
        access_token = form.access_token.data
        params = {'limit':'50'}
        headers = {'Accept':'application/json','Authorization':access_token}
        spotify_request = requests.get(spotify_url, headers=headers, params=params)
        spotify_results = json.loads(spotify_request.text)

        for item in spotify_results['items']:
            songname = item['track']['name']
            artistname = item['track']['artists'][0]['name']
            artist = Artist.query.filter_by(artistname=artistname).first()
            if not artist:
                artist = Artist(artistname=artistname)
                db.session.add(artist)
                db.session.commit()
            song = Song.query.filter_by(songname=songname).first()
            if not song:
                song = Song(songname=songname, artistid=artist.id)
                db.session.add(song)
                db.session.commit()

        return redirect(url_for('home'))

    errors = [v for v in form.errors.values()]
    if len(errors) > 0:
        flash("!!!! ERRORS IN FORM SUBMISSION - " + str(errors))
    return render_template('base.html', form=form)

@app.route('/names')
def all_names():
    names = User.query.all()
    return render_template('name_example.html', names=names)

@app.route('/artistsearch')
def specific_artist():
    form = ArtistForm()
    return render_template('artist_search.html', form=form)

@app.route('/artistsearchresults', methods=['GET', 'POST'])
def search_results():
    form = ArtistForm()
    if request.args:
        artistname = request.args.get('artist')
        artist = Artist.query.filter_by(artistname=artistname).first()
        if not artist:
            flash("Artist not in users' listening history, try another artist!")
            return redirect(url_for('specific_artist'))
        songs = Song.query.filter_by(artistid=artist.id).all()
        return render_template('artist_results.html', artistname=artistname, songs=songs)
    return redirect(url_for('specific_artist'))


@app.route('/suggestions', methods=['GET', 'POST'])
def suggested_songs():
    form = SuggestionForm()
    if request.method == 'POST':
        songname = request.form['songname']
        artistname = request.form['artistname']
        rating = request.form['rating']

        suggestion = Suggested(songname=songname, artistname=artistname, rating=rating)
        db.session.add(suggestion)
        db.session.commit()

        suggestions = Suggested.query.all()
        return render_template('suggestions.html', form=form, suggestions=suggestions)
    return render_template('suggestions.html', form=form)


## Code to run the application...
if __name__ == '__main__':
    db.create_all() # Will create any defined models when you run the application
    app.run(use_reloader=True,debug=True)
# Put the code to do so here!
# NOTE: Make sure you include the code you need to initialize the database structure when you run the application!
