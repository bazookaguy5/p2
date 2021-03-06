from lists import lists
from flask import Blueprint, request, redirect, render_template, current_app, url_for
import os

from item import Item
from DBHandler import DBHandler

admin = Blueprint('admin', __name__, template_folder='templates')


@admin.route('/admin')
def blank_admin_page(invalid=False):
    return redirect(url_for('admin.admin_page', gender='all', category='all', page_no=1, invalid=invalid))


@admin.route('/admin/<gender>')
def gender_admin_page(gender, invalid=False):
    return redirect(url_for('admin.admin_page', gender=gender, category='all', page_no=1, invalid=invalid))


@admin.route('/admin/<gender>/<category>')
def page_admin_page(gender, category, invalid=False):
    return redirect(url_for('admin.admin_page', gender=gender, category=category, page_no=1, invalid=invalid))


@admin.route('/admin/<gender>/<category>/<int:page_no>')
def admin_page(gender, category, page_no, invalid=False):
    if request.cookies.get('user') != 'admin':
        return redirect(url_for('index'))

    sort_list = {'new': 'date_added DESC', 'a-z': 'title ASC', 'z-a': 'title DESC', 'low-high': 'price ASC', 'high-low': 'price DESC'}

    color = request.args.get('color') if request.args.get('color') else '%'
    show = int(request.args.get('show')) if request.args.get('show') else 12
    price_start = int(request.args.get('start_amount')) if request.args.get('start_amount') else 0
    price_end = int(request.args.get('end_amount')) if request.args.get('end_amount') else 100000
    sort_by = sort_list[request.args.get('sort_by')] if request.args.get('sort_by') else sort_list['new']

    # Checking whether all values provided are correct
    if (gender not in lists['genders'] and gender != 'all') or\
            (category not in lists[gender+'_categories'] and category != 'all'):
        return redirect(url_for('admin.blank_admin_page'))

    db = DBHandler(current_app.config['DATABASEIP'], current_app.config['PORT'], current_app.config['DB_USER'],
                   current_app.config['DB_PASSWORD'], current_app.config['DATABASE'])
    items = db.get_items(color, gender, category, price_start, price_end, sort_by)
    upper_limit = show * page_no
    lower_limit = upper_limit - show

    return render_template('admin.html',  lists=lists, page_name='admin', gender_main=gender, category_main=category, page_no_main=page_no,
                           invlaid=invalid, items=items[lower_limit:upper_limit], pages=int((len(items)/show)+1),
                           show=show, start_amount=price_start, end_amount=price_end, sort_by=sort_by)


@admin.route('/add_item', methods=['POST'])
def admin_add_item():
    if request.cookies.get('user') != 'admin':
        return redirect(url_for('index'))

    gender, category, page_no = request.referrer.split('/')[4:]
    page_no = int(page_no.split('?')[0])
    try:
        item = [
            request.form.get('title'),
            request.form.get('color'),
            int(request.form.get('quantity')),
            request.form.get('category'),
            request.form.get('gender'),
            int(request.form.get('price')),
            request.form.get('manufacturer'),
        ]

        if validate_form_data(item) and \
                request.files['picture'].content_type != 'images/png':
            db = DBHandler(current_app.config['DATABASEIP'], current_app.config['PORT'], current_app.config['DB_USER'],
                           current_app.config['DB_PASSWORD'], current_app.config['DATABASE'])
            serial_number = db.store_item(item)
            if serial_number is not None:
                file = request.files['picture']
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], serial_number + ".png"))
            else:
                pass
                # do something for error

            return redirect(url_for('admin.admin_page', gender=item[4], category=item[3], page_no=page_no))
    except Exception as e:
        print(e)

    return redirect(url_for('admin.admin_page', gender=gender, category=category, page_no=page_no, invalid=True))


@admin.route("/delete/<serial>")
def delete(serial):
    if request.cookies.get('user') != 'admin':
        return redirect(url_for('index'))

    gender, category, page_no = request.referrer.split('/')[4:]
    page_no = int(page_no.split('?')[0])

    try:
        int(serial)  # Checking if the serial is a number
        db = DBHandler(current_app.config['DATABASEIP'], current_app.config['PORT'], current_app.config['DB_USER'],
                       current_app.config['DB_PASSWORD'], current_app.config['DATABASE'])
        db.delete_item(serial)
        os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], serial + ".png"))
    finally:
        return redirect(url_for('admin.admin_page', gender=gender, category=category, page_no=1))


@admin.route("/edit_item/<serial>", methods=['POST'])
def edit_item(serial):
    if request.cookies.get('user') != 'admin':
        return redirect(url_for('index'))

    gender, category, page_no = request.referrer.split('/')[4:]
    page_no = int(page_no.split('?')[0])
    try:
        int(serial)
        item = [
            request.form.get('title'),
            request.form.get('color'),
            int(request.form.get('quantity')),
            request.form.get('category'),
            request.form.get('gender'),
            int(request.form.get('price')),
            request.form.get('manufacturer'),
        ]
        if validate_form_data(item):
            db = DBHandler(current_app.config['DATABASEIP'], current_app.config['PORT'], current_app.config['DB_USER'],
                           current_app.config['DB_PASSWORD'], current_app.config['DATABASE'])
            db.change_item(serial, item)
            if request.files['picture'].filename != '' and request.files['picture'].content_type != 'images/png':
                file = request.files['picture']
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], serial + ".png"))
            else:
                pass
                # do something for error

            return redirect(url_for('admin.admin_page', gender=gender, category=category, page_no=page_no))
        else:
            return redirect(url_for('admin.admin_page', gender=gender, category=category, page_no=page_no, invalid=True))  # add some form of reply with 'invalid form data'
    except Exception as e:
        print(e)
        return redirect(url_for('admin.admin_page', gender=gender, category=category, page_no=page_no, invalid=True))


def validate_form_data(item):
    """Checks validity of the form data"""
    for field in item:
        if field == '':
            return False

    if len(item[0]) > 30 or \
            item[1] not in lists['colors'] or \
            item[2] < 1 or \
            item[4] not in lists['genders'] or \
            item[3] not in lists[item[4] + '_categories'] or \
            item[5] < 0:
        return False

    return True

