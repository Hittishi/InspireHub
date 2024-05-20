from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import login_required, current_user
from .models import User, Note, Like, Comment
from .import db
import json
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import desc


# Bunch of urls in the app is Blueprint
views = Blueprint('views', __name__)


@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    notes = Note.query.order_by(desc(Note.date)).all()
    for note in notes:
        note.comments = Comment.query.filter_by(note_id=note.id).all()
        note.like_count = Like.query.filter_by(note_id=note.id).count()
        note.liked_by_user = Like.query.filter_by(
            note_id=note.id, user_id=current_user.id).first() is not None
    return render_template('home.html', user=current_user, notes=notes)


@views.route('/delete-note', methods=['POST'])
def delete_note():
    note = json.loads(request.data)
    noteId = note['noteId']
    note = Note.query.get(noteId)
    if note:
        if note.user_id == current_user.id:  # user that signed in owns the note
            db.session.delete(note)
            db.session.commit()
    return jsonify({})


@views.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        note = request.form.get('note')
        if len(note) < 1:
            flash('Note is too short', category='error')
        else:
            new_note = Note(data=note, user_id=current_user.id)
            db.session.add(new_note)
            db.session.commit()
            flash('Note is Added', category='success')

    return render_template('profile.html', user=current_user)


@views.route('/like-note', methods=['POST'])
@login_required
def like_note():
    data = json.loads(request.data)
    noteId = data['noteId']
    note = Note.query.get(noteId)
    if note:
        like = Like.query.filter_by(
            note_id=noteId, user_id=current_user.id).first()
        if like:
            db.session.delete(like)
            db.session.commit()
            return jsonify({'success': True, 'liked': False})
        else:
            new_like = Like(note_id=noteId, user_id=current_user.id)
            db.session.add(new_like)
            db.session.commit()
            return jsonify({'success': True, 'liked': True})
    return jsonify({'success': False})


@views.route('/add-comment', methods=['POST'])
@login_required
def add_comment():
    data = json.loads(request.data)
    noteId = data['noteId']
    commentText = data['comment'].strip()  # Trim whitespace
    if len(commentText) < 1:
        flash('Comment cannot be empty.', category='error')
        return jsonify({'success': False})

    note = Note.query.get(noteId)
    if note:
        new_comment = Comment(
            data=commentText, user_id=current_user.id, note_id=note.id)
        db.session.add(new_comment)
        db.session.commit()
        return jsonify({'success': True, 'comment': {
            'user': current_user.firstName,
            'data': commentText,
            'date': new_comment.date.strftime('%Y-%m-%d %H:%M:%S')
        }})
    return jsonify({'success': False})


@views.route('/delete-comment', methods=['POST'])
@login_required
def delete_comment():
    data = json.loads(request.data)
    commentId = data['commentId']
    comment = Comment.query.get(commentId)
    if comment and comment.user_id == current_user.id:
        db.session.delete(comment)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})


@views.route('/settings')
@login_required
def settings_page():
    return render_template('settings.html', user=current_user)

# Route to handle updating personal information from the settings page


@views.route('/update-profile', methods=['POST'])
@login_required
def update_profile_settings():
    if request.method == 'POST':
        new_first_name = request.form.get('firstName')
        new_email = request.form.get('email')
        new_password = request.form.get('newPassword')
        confirm_password = request.form.get('confirmPassword')

        # Update user's first name and email
        current_user.firstName = new_first_name
        current_user.email = new_email

        # Check if new password and confirm password match
        if new_password != confirm_password:
            flash('Passwords do not match', category='error')
            return redirect(url_for('views.settings_page'))

        # Update password if new password is provided
        if new_password:
            current_user.password = (generate_password_hash(
                new_password, method='pbkdf2:sha256'))

        # Commit changes to the database
        db.session.commit()
        flash('Personal information updated successfully', category='success')

    return redirect(url_for('views.settings_page'))

# Route to handle updating personal information


# Route to handle updating a note


@views.route('/update-note/<int:note_id>', methods=['POST'])
@login_required
def update_note(note_id):
    if request.method == 'POST':
        new_note_text = request.form.get('note')

        # Retrieve the note from the database
        note = Note.query.get(note_id)

        # Check if the note belongs to the current user
        if note.user_id == current_user.id:
            # Update the note text
            note.data = new_note_text

            # Commit changes to the database
            db.session.commit()
            flash('Note updated successfully', category='success')
        else:
            flash('You do not have permission to edit this note', category='error')

    return redirect(url_for('views.settings_page'))
