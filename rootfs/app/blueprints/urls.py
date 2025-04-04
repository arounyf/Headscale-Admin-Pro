import json
from flask_login import current_user, login_required
from sqlalchemy import func
from app.blueprints.admin import admin
import requests

from login_setup import role_required
from models import UserModel,NodeModel
from flask import Blueprint, render_template,request, session, make_response, g, redirect, url_for, jsonify, \
    current_app

def next_url(default_endpoint='/'):
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
    else:
       next_url = request.args.get('next') or url_for(default_endpoint)
       return redirect(next_url)
    
 