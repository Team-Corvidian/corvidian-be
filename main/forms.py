from django import forms

class ConsultationForm(forms.Form):
    name = forms.CharField(label="Nama", max_length=100)
    email = forms.EmailField(label="Email")
    phone = forms.CharField(label="Nomor Telepon", max_length=20)
    company = forms.CharField(label="Perusahaan", max_length=150)
    question = forms.CharField(label="Pertanyaan", widget=forms.Textarea)
    agreement = forms.BooleanField(required=True)
