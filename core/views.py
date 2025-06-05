# Create your views here.
from django.db import IntegrityError
from django.db.backends.utils import logger
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.http import urlsafe_base64_decode
from sqlparse.sql import Comment
from .forms import UserRegisterForm, PostForm, AnnouncementForm, EventForm, CommentForm, MessageForm
from .models import Post, Announcement, Event, EventRegistration, CourseGrade
from django.db import models
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import CustomPasswordResetForm
from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordResetConfirmView
from django.contrib.auth import get_user_model
from .forms import CustomUserCreationForm
from smtplib import SMTPException
from django.core.mail import BadHeaderError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

def home(request):
    announcements = Announcement.objects.order_by('-created_at')[:5]
    events = Event.objects.order_by('-start_time')[:5]
    posts = Post.objects.order_by('-created_at')[:5]
    return render(request, 'core/home.html', {'announcements': announcements, 'events': events, 'posts': posts})


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                # 创建新用户并保存
                user = form.save(commit=False)

                # 设置额外的用户字段
                user.email = form.cleaned_data['email']
                user.student_id = form.cleaned_data['student_id']
                user.full_name = form.cleaned_data['full_name']

                # 保存用户
                user.save()

                # 自动登录新用户
                login(request, user)
                return redirect('home')

            except IntegrityError:
                # 处理可能出现的唯一性冲突
                form.add_error(None, "注册失败，请检查您的学号和邮箱是否已被使用")
                return render(request, 'core/register.html', {'form': form})
        else:
            # 表单无效，重新显示带错误信息的表单
            return render(request, 'core/register.html', {'form': form})
    else:
        form = CustomUserCreationForm()

    return render(request, 'core/register.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        # 获取表单数据
        email = request.POST.get('email')
        password = request.POST.get('password')

        # 使用自定义用户模型
        User = get_user_model()

        try:
            # 尝试通过邮箱查找用户
            user = User.objects.get(email=email)
            # 使用用户名进行身份验证
            authenticated_user = authenticate(
                request,
                username=user.username,
                password=password
            )

            if authenticated_user is not None:
                login(request, authenticated_user)
                return redirect('home')
            else:
                # 如果密码错误
                messages.error(request, '邮箱或密码错误，请重试')
                return render(request, 'core/login.html')  # 改为渲染而不是重定向
        except User.DoesNotExist:
            # 如果用户不存在
            messages.error(request, '该邮箱未注册，请检查邮箱地址')
            return render(request, 'core/login.html')  # 改为渲染而不是重定向
    else:
        # 处理GET请求
        return render(request, 'core/login.html')

def user_logout(request):
    logout(request)
    return redirect('home')


# 帖子视图
@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('post_detail', post_id=post.id)
    else:
        form = PostForm()
    return render(request, 'core/post_form.html', {'form': form})


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id, author=request.user)
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            # 处理删除附件请求
            delete_attachment = request.POST.get('delete_attachment', False)
            if delete_attachment and post.attachment:
                post.attachment.delete()
                post.attachment = None

            # 保存更新
            post = form.save(commit=False)
            if 'attachment' in request.FILES:
                post.attachment = request.FILES['attachment']
            post.save()
            return redirect('post_detail', post_id=post.id)
    else:
        form = PostForm(instance=post)

    return render(request, 'core/post_form.html', {
        'form': form,
        'post': post,
        'is_edit': True
    })


@login_required
def post_delete(request, post_id):
    post = get_object_or_404(Post, id=post_id, author=request.user)
    if request.method == 'POST':
        # 删除附件
        if post.attachment:
            post.attachment.delete()
        post.delete()
        messages.success(request, '帖子已删除')
        return redirect('post_list')

    return render(request, 'core/post_confirm_delete.html', {'post': post})


# 更新现有的post_detail视图
@login_required
def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    # 权限检查 - 仅允许可见范围内的用户查看
    user_class = request.user.class_belong
    can_view = False

    if post.visibility == 'all':  # 全校可见
        can_view = True
    elif post.visibility == 'major' and user_class and user_class.major == post.author.class_belong.major:
        can_view = True
    elif post.visibility == 'grade' and user_class and user_class.grade == post.author.class_belong.grade:
        can_view = True
    elif post.visibility == 'class' and user_class and user_class == post.author.class_belong:
        can_view = True
    elif request.user == post.author:  # 作者总是可以查看自己的帖子
        can_view = True

    if not can_view:
        return render(request, 'core/permission_denied.html', status=403)

    # 评论处理
    comments = post.comments.all().order_by('-created_at')
    comment_form = CommentForm(request.POST or None)

    # 更新评论处理以支持匿名
    if request.method == 'POST' and request.user.is_authenticated:
        form = CommentForm(request.POST or None)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.anonymous = bool(request.POST.get('anonymous'))
            comment.save()
            return redirect('post_detail', post_id=post.id)

    return render(request, 'core/post_detail.html', {
        'post': post,
        'comments': comments,
        'form': comment_form
    })


@login_required
def post_list(request):
    # 获取当前用户所属范围
    user_class = request.user.class_belong
    user_grade = user_class.grade if user_class else None
    user_major = user_class.major if user_class else None

    # 根据可见范围筛选帖子
    post_list = Post.objects.filter(
        models.Q(visibility='all') |  # 全校范围
        models.Q(visibility='major', author__class_belong__major=user_major) |  # 同专业
        models.Q(visibility='grade', author__class_belong__grade=user_grade) |  # 同年级
        models.Q(visibility='class', author__class_belong=user_class) |  # 同班级
        models.Q(author=request.user)  # 当前用户自己的帖子
    ).distinct().order_by('-created_at')

    # 分页
    paginator = Paginator(post_list, 10)  # 每页10条
    page = request.GET.get('page')

    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)

    return render(request, 'core/post_list.html', {'posts': posts})


# 更新post_create视图支持附件
@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user

            # 处理附件
            if 'attachment' in request.FILES:
                post.attachment = request.FILES['attachment']

            post.save()
            return redirect('post_detail', post_id=post.id)
    else:
        form = PostForm()

    return render(request, 'core/post_form.html', {'form': form})

@login_required
def post_remove_attachment(request, post_id):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        post = get_object_or_404(Post, id=post_id, author=request.user)
        if post.attachment:
            post.attachment.delete()
            post.attachment = None
            post.save()
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'message': '无附件可删除'})
    return JsonResponse({'success': False, 'message': '无效请求'}, status=400)


# 评论编辑视图
@login_required
def comment_edit(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, author=request.user)

    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect('post_detail', post_id=comment.post.id)
    else:
        form = CommentForm(instance=comment)

    return render(request, 'core/comment_form.html', {
        'form': form,
        'comment': comment
    })


# 评论删除视图
@login_required
def comment_delete(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, author=request.user)
    post_id = comment.post.id

    if request.method == 'POST':
        comment.delete()
        messages.success(request, '评论已删除')
        return redirect('post_detail', post_id=post_id)

    return render(request, 'core/comment_confirm_delete.html', {
        'comment': comment
    })

#通知列表视图
@login_required
def announcement_create(request):
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES)
        if form.is_valid():
            ann = form.save(commit=False)
            ann.author = request.user
            # 如果需要关联班级，可以添加
            if request.user.class_belong:
                ann.class_belong = request.user.class_belong
            ann.save()
            return redirect('home')
    else:
        form = AnnouncementForm()


    return render(request, 'core/announcement_detail.html', {'form': form})


@login_required
def announcement_manage(request):
    """公告管理视图 - 包含创建和列表展示"""
    # 处理表单提交（创建或更新）
    announcement_id = request.GET.get('edit')
    editing = False
    announcement = None

    if announcement_id:
        # 尝试获取公告对象并检查用户权限
        try:
            announcement = Announcement.objects.get(id=announcement_id)
            # 确保只有公告的作者才能编辑
            if announcement.author != request.user:
                return render(request, 'core/permission_denied.html', status=403)
            editing = True
        except Announcement.DoesNotExist:
            return render(request, 'core/404.html', status=404)

    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES, instance=announcement)
        if form.is_valid():
            # 如果是编辑，使用现有实例；否则创建新实例
            if not editing:
                announcement = Announcement(author=request.user)

            # 更新公告数据
            announcement.title = form.cleaned_data['title']
            announcement.content = form.cleaned_data['content']
            announcement.category = form.cleaned_data['category']
            announcement.scope = form.cleaned_data['scope']
            announcement.is_pinned = form.cleaned_data['is_pinned']

            # 处理附件
            if 'attachment' in request.FILES:
                announcement.attachment = request.FILES['attachment']

            announcement.save()
            return redirect('announcement_manage')
    else:
        # 初始化表单
        form = AnnouncementForm(instance=announcement)

    # 获取公告列表并分页
    announcements_list = Announcement.objects.filter(author=request.user).order_by('-created_at')
    paginator = Paginator(announcements_list, 10)  # 每页10个公告

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/announcement_manage.html', {
        'form': form,
        'announcements': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'editing': editing,
        'announcement': announcement
    })


@login_required
def announcement_delete(request, announcement_id):
    """删除公告视图"""
    announcement = get_object_or_404(Announcement, id=announcement_id, author=request.user)
    if request.method == 'POST':
        announcement.delete()
        return redirect('announcement_manage')
    return render(request, 'core/announcement_confirm_delete.html', {'announcement': announcement})


@login_required
def announcement_list(request):
    """公告列表视图 - 所有用户可见"""
    # 获取当前用户所属范围
    user_class = request.user.class_belong
    user_grade = user_class.grade if user_class else None
    user_major = user_class.major if user_class else None

    # 根据可见范围筛选公告
    announcements = Announcement.objects.filter(
        models.Q(scope='school') |  # 全校范围的公告
        models.Q(scope='major', author__class_belong__major=user_major) |  # 同专业范围的公告
        models.Q(scope='grade', author__class_belong__grade=user_grade) |  # 同年级范围的公告
        models.Q(scope='class', author__class_belong=user_class)  # 同班级范围的公告
    ).distinct().order_by('-is_pinned', '-created_at')

    # 分页处理
    paginator = Paginator(announcements, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/announcement_list.html', {
        'announcements': page_obj,
        'is_paginated': paginator.num_pages > 1
    })


@login_required
def announcement_detail(request, announcement_id):
    """公告详情视图"""
    # 尝试获取公告对象
    try:
        announcement = Announcement.objects.get(id=announcement_id)
    except Announcement.DoesNotExist:
        return render(request, 'core/404.html', status=404)

    # 检查用户是否有权限查看此公告（根据可见范围）
    user_class = request.user.class_belong
    can_view = False

    # 检查公告的可见范围
    if announcement.scope == 'school':  # 全校可见
        can_view = True
    elif announcement.scope == 'major' and user_class and user_class.major == announcement.class_belong.major:
        can_view = True
    elif announcement.scope == 'grade' and user_class and user_class.grade == announcement.class_belong.grade:
        can_view = True
    elif announcement.scope == 'class' and user_class and user_class == announcement.class_belong:
        can_view = True

    # 自己发布的公告自己一定可见
    if announcement.author == request.user:
        can_view = True
    elif announcement.scope == 'school':  # 全校可见
        can_view = True
    elif announcement.scope == 'major' and user_class and user_class.major == announcement.class_belong.major:
        can_view = True
    elif announcement.scope == 'grade' and user_class and user_class.grade == announcement.class_belong.grade:
        can_view = True
    elif announcement.scope == 'class' and user_class and user_class == announcement.class_belong:
        can_view = True
        
    # 如果用户没有权限查看
    if not can_view:
        return render(request, 'core/permission_denied.html', status=403)

    # 渲染详情页面
    return render(request, 'core/announcement_detail.html', {
        'announcement': announcement
    })


@login_required
def remove_announcement_attachment(request, announcement_id):
    """移除公告附件"""
    announcement = get_object_or_404(Announcement, id=announcement_id, author=request.user)

    if request.method == 'POST':
        # 删除附件文件
        if announcement.attachment:
            announcement.attachment.delete()
            announcement.attachment = None
            announcement.save()

        return redirect('announcement_manage')

    # 如果是GET请求，重定向到管理页面
    return redirect('announcement_manage')


#活动视图
@login_required
def event_create(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.creator = request.user
            event.save()
            return redirect('event_detail', event_id=event.id)
    else:
        form = EventForm()
    return render(request, 'core/event_form.html', {'form': form})


@login_required
def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    signed_up = EventRegistration.objects.filter(event=event, user=request.user).exists()
    participants = event.registrations.all()[:10]  # 显示前10位参与者

    return render(request, 'core/event_detail.html', {
        'event': event,
        'signed_up': signed_up,
        'participants': participants,
        'can_edit': event.creator == request.user
    })

@login_required
def event_signup(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if not EventRegistration.objects.filter(event=event, user=request.user).exists():
        EventRegistration.objects.create(event=event, user=request.user)
    return redirect('event_detail', event_id=event.id)

@login_required
def event_list(request):
    # 错误：events = Event.objects.all().order_by('-created_at')
    # 正确：使用新添加的 created_at 字段
    events = Event.objects.all().order_by('-created_at')

    # 或者使用 start_time 字段（如果业务需要）
    # events = Event.objects.all().order_by('-start_time')

    return render(request, 'core/event_list.html', {'events': events})


@login_required
def event_edit(request, event_id):
    event = get_object_or_404(Event, id=event_id, creator=request.user)

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            return redirect('event_detail', event_id=event.id)
    else:
        form = EventForm(instance=event)

    return render(request, 'core/event_form.html', {
        'form': form,
        'is_edit': True,
        'event': event
    })


@login_required
def event_delete(request, event_id):
    event = get_object_or_404(Event, id=event_id, creator=request.user)

    if request.method == 'POST':
        event.delete()
        return redirect('event_list')

    return render(request, 'core/event_confirm_delete.html', {'event': event})

@login_required
def calendar_view(request):
    """活动日历视图"""
    events = Event.objects.filter(end_time__gte=timezone.now())
    return render(request, 'core/event_calendar.html', {'events': events})

@login_required
def past_events(request):
    """历史活动视图"""
    past_events = Event.objects.filter(end_time__lt=timezone.now()).order_by('-start_time')
    return render(request, 'core/past_events.html', {'events': past_events})

@login_required
def user_events(request):
    """用户参与的活动"""
    registrations = EventRegistration.objects.filter(user=request.user).select_related('event')
    events = [reg.event for reg in registrations]
    return render(request, 'core/user_events.html', {'events': events})

@login_required
def popular_events(request):
    """热门活动"""
    popular_events = Event.objects.annotate(
        participants_count=Count('registrations')
    ).order_by('-participants_count')[:10]
    return render(request, 'core/popular_events.html', {'events': popular_events})

# 个人主页

@login_required
def own_profile(request):
    """显示当前用户的个人主页"""
    return profile(request, user_id=request.user.id)


@login_required
def profile(request, user_id):
    # 获取用户模型
    UserModel = get_user_model()
    profile_user = get_object_or_404(UserModel, id=user_id)

    # 过滤公开可见的留言
    if request.user != profile_user:
        messages = profile_user.received_messages.filter(visible_to_public=True)
    else:
        messages = profile_user.received_messages.all()

    form = MessageForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        msg = form.save(commit=False)
        msg.sender = request.user
        msg.receiver = profile_user
        msg.save()
        # 重定向到当前用户的个人主页（不需要ID）
        return redirect('own_profile')

    return render(request, 'core/profile.html', {
        'profile_user': profile_user,
        'messages': messages,
        'form': form
    })


@login_required
def profile_edit(request):
    if request.method == 'POST':
        # 处理表单数据
        user = request.user

        # 更新基本信息
        user.full_name = request.POST.get('full_name', '')
        user.nickname = request.POST.get('nickname', '')
        user.bio = request.POST.get('bio', '')
        user.phone_number = request.POST.get('phone_number', '')
        user.email = request.POST.get('email', '')
        user.college = request.POST.get('college', '')
        user.class_name = request.POST.get('class_name', '')
        user.self_message = request.POST.get('self_message', '')

        # 处理头像
        if 'remove_avatar' in request.POST and user.avatar:
            user.avatar.delete()
            user.avatar = None

        if 'avatar' in request.FILES:
            if user.avatar:  # 删除旧头像
                user.avatar.delete()
            user.avatar = request.FILES['avatar']

        user.save()
        # ... 更新资料 ...
        messages.success(request, '个人资料已更新')
        # 重定向到当前用户的个人主页（不需要ID）
        return redirect('own_profile')

    return render(request, 'core/profile_edit.html')


# 成绩页面
@login_required
def my_grades(request):
    UserModel = get_user_model()  # <-- 先获取用户模型类
    # 确保查询时使用实际的模型类
    grades = CourseGrade.objects.filter(student=request.user)
    return render(request, 'core/grade_view.html', {'grades': grades})


# def filter_by_visibility(queryset, user):
#     return queryset.filter(
#         models.Q(visibility='public') |
#         models.Q(visibility='class') |
#         models.Q(author=user)
#     )
# # , author__class_id=user.class_id

def filter_posts(queryset, user):
    """筛选帖子的可见范围"""
    return queryset.filter(
        models.Q(visibility='public') |
        models.Q(visibility='class') |
        models.Q(author=user)
    )


def filter_announcements(queryset, user):
    """筛选公告的可见范围 - 使用正确的 scope 字段"""
    # 获取用户信息用于筛选，考虑到 class_belong 可能为 None
    user_class = user.class_belong
    user_grade = user_class.grade if user_class else None
    user_major = user_class.major if user_class else None

    # 构造查询条件
    query = models.Q(scope='school')  # 全校范围

    # 添加基于专业的筛选
    if user_major:
        query |= models.Q(scope='major', class_belong__major=user_major)

    # 添加基于年级的筛选
    if user_grade:
        query |= models.Q(scope='grade', class_belong__grade=user_grade)

    # 添加基于班级的筛选
    if user_class:
        query |= models.Q(scope='class', class_belong=user_class)

    # 总是显示用户自己发布的公告
    query |= models.Q(author=user)

    return queryset.filter(query)


def filter_events(queryset, user):
    """筛选事件的可见范围"""
    return queryset.filter(
        models.Q(visibility='public') |
        models.Q(visibility='class') |
        models.Q(creator=user)
    )


@login_required
def home(request):
    # 使用更新后的筛选函数
    posts = filter_posts(Post.objects.all(), request.user).order_by('-created_at')[:5]
    announcements = filter_announcements(Announcement.objects.all(), request.user).order_by('-created_at')[:5]
    events = filter_events(Event.objects.all(), request.user).order_by('-start_time')[:5]

    return render(request, 'core/home.html', {
        'posts': posts,
        'announcements': announcements,
        'events': events
    })


# 搜索
def search(request):
    query = request.GET.get('q')
    return render(request, 'search.html', {'query': query})


def forgot_password(request):
    if request.method == 'POST':
        form = CustomPasswordResetForm(request.POST)
        if form.is_valid():
            try:
                email_sent = form.send_email(request)
                if email_sent:
                    messages.success(request, '密码重置邮件已发送，请检查您的邮箱。')
                    return redirect('login')
                else:
                    messages.error(request, '邮件发送失败。请联系管理员寻求帮助。')
            except (BadHeaderError, SMTPException) as e:
                logger.error(f"邮件发送错误: {e}")
                messages.error(request, f'邮件发送出错: {e}')
            except Exception as e:
                logger.exception("发送邮件时发生未处理异常")
                messages.error(request, '发送邮件时出现意外错误。')
        else:
            messages.error(request, '请填写正确的邮箱地址。')
    else:
        form = CustomPasswordResetForm()

    return render(request, 'core/forgot_password.html', {'form': form})


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'core/reset_password.html'
    success_url = reverse_lazy('password_reset_complete')

    # 覆盖用户获取方法以使用自定义用户模型
    def get_user(self, uidb64):
        User = get_user_model()
        try:
            # urlsafe_base64_decode() 在 Python 3 返回 bytes，需要解码
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User._default_manager.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        return user


def password_reset_complete(request):
    messages.success(request, '您的密码已重置成功！请使用新密码登录')
    return redirect('login')