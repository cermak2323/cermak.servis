from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from models import User

class CreateUserForm(FlaskForm):
    username = StringField('Kullanıcı Adı', validators=[DataRequired(), Length(min=4, max=50)])
    password = PasswordField('Şifre', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Şifreyi Onayla', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Rol', choices=[('admin', 'Admin'), ('servis', 'Servis'), ('muhendis', 'Mühendis'), ('musteri', 'Müşteri')], validators=[DataRequired()])
    can_view_parts = BooleanField('Parça Görüntüleme')
    can_edit_parts = BooleanField('Parça Düzenleme')
    can_view_purchase_prices = BooleanField('Geliş Fiyatlarını Görüntüleme')  # Yeni eklenen alan
    can_view_catalogs = BooleanField('Katalog Görüntüleme')
    can_view_maintenance = BooleanField('Bakım Görüntüleme')
    can_edit_maintenance = BooleanField('Bakım Düzenleme')
    can_view_faults = BooleanField('Arıza Görüntüleme')
    can_add_fault_solutions = BooleanField('Çözüm Ekleme')
    can_view_contact = BooleanField('İletişim Görüntüleme')
    can_view_admin_panel = BooleanField('Admin Panel Görüntüleme')
    can_create_offers = BooleanField('Teklif Oluşturma')
    can_upload_excel = BooleanField('Excel Yükleme')
    submit = SubmitField('Kullanıcı Oluştur')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Bu kullanıcı adı zaten mevcut. Lütfen başka bir kullanıcı adı seçin.')