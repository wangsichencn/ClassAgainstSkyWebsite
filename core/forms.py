from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import Post, Announcement, Event, Comment, Message
from django.contrib.auth import get_user_model

User = get_user_model()


class UserRegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'full_name', 'student_id', 'password1', 'password2')

    def clean_student_id(self):
        student_id = self.cleaned_data['student_id']
        if User.objects.filter(student_id=student_id).exists():
            raise forms.ValidationError("此学号已被注册")
        return student_id

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("此邮箱已被注册")
        return email

# 更新PostForm以支持附件
class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'anonymous', 'visibility', 'attachment']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5}),
        }
        labels = {
            'attachment': '上传附件',
        }


# 添加CommentForm的更新版本
class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content', 'anonymous']  # 添加匿名字段

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].widget.attrs.update({
            'class': 'form-control',
            'rows': 3
        })


# 更新 AnnouncementForm 类
class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        # 使用模型中的实际字段名：scope 替代 visibility
        fields = ['title', 'content', 'category', 'scope', 'is_pinned', 'attachment']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5}),
        }
        labels = {
            'is_pinned': '置顶此公告',
        }


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'event_type', 'location', 'start_time', 'end_time', 'visibility']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    # 添加下拉框选项
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['event_type'].widget = forms.Select(choices=Event.EVENT_TYPE_CHOICES)


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content', 'visible_to_public']


class CustomPasswordResetForm(forms.Form):
    email = forms.EmailField(
        label="邮箱地址",
        max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'class': 'form-control'})
    )

    def send_email(self, request):
        """发送密码重置邮件"""
        User = get_user_model()
        email = self.cleaned_data["email"]
        try:
            # 使用自定义用户模型查询用户
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return False  # 表示用户不存在

        # 生成重置令牌
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # 构建重置URL
        reset_url = request.build_absolute_uri(
            reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        )

        # 发送邮件
        subject = '班级网站 - 重置您的密码'
        message = render_to_string('core/email/reset_password_email.txt', {
            'user': user,
            'reset_url': reset_url,
        })

        send_mail(
            subject,
            message,
            'noreply@classwebsite.com',  # 修改为你的发送邮箱
            [email],
            fail_silently=False,
        )
        return True  # 表示邮件发送成功


User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    # 确保所有必填字段都有帮助文本和标签
    email = forms.EmailField(
        label='邮箱地址',
        help_text='必需：您的有效邮箱地址'
    )
    student_id = forms.CharField(
        label='学号',
        help_text='必需：您的唯一学号'
    )
    full_name = forms.CharField(
        label='真实姓名',
        help_text='必需：您的真实姓名'
    )

    class Meta:
        model = User
        fields = ("email", "username", "student_id", "full_name", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("该邮箱已被注册")
        return email

    def clean_student_id(self):
        student_id = self.cleaned_data['student_id']
        if User.objects.filter(student_id=student_id).exists():
            raise forms.ValidationError("该学号已被使用")
        return student_id

    def clean_username(self):
        username = self.cleaned_data['username']
        if not username:  # 确保用户名非空
            raise forms.ValidationError("用户名不能为空")
        return username