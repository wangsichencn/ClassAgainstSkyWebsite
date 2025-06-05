from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

    # path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),

urlpatterns = [
    path('', views.home, name='home'),

    # 认证相关
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    # 帖子功能
    path('posts/', views.post_list, name='post_list'),
    path('post/create/', views.post_create, name='post_create'),
    path('post/<int:post_id>/', views.post_detail, name='post_detail'),
    path('post/<int:post_id>/edit/', views.post_edit, name='post_edit'),
    path('post/<int:post_id>/delete/', views.post_delete, name='post_delete'),
    path('post/<int:post_id>/remove-attachment/', views.post_remove_attachment, name='post_remove_attachment'),

    # 评论管理
    path('comment/<int:comment_id>/edit/', views.comment_edit, name='comment_edit'),
    path('comment/<int:comment_id>/delete/', views.comment_delete, name='comment_delete'),

    # 公告相关URL
    path('announcements/', views.announcement_list, name='announcement_list'),
    path('announcements/manage/', views.announcement_manage, name='announcement_manage'),
    path('announcements/<int:announcement_id>/', views.announcement_detail, name='announcement_detail'),
    path('announcements/<int:announcement_id>/delete/', views.announcement_delete, name='announcement_delete'),

    # 移除附件
    path('announcements/<int:announcement_id>/remove-attachment/',
         views.remove_announcement_attachment,
         name='remove_announcement_attachment'),

    # 活动 Event
    path('events/create/', views.event_create, name='event_create'),
    path('events/<int:event_id>/', views.event_detail, name='event_detail'),
    path('events/<int:event_id>/edit/', views.event_edit, name='event_edit'),
    path('events/<int:event_id>/delete/', views.event_delete, name='event_delete'),
    path('events/<int:event_id>/signup/', views.event_signup, name='event_signup'),
    path('events/', views.event_list, name='event_list'),
    path('events/calendar/', views.calendar_view, name='calendar_view'),
    path('events/past/', views.past_events, name='past_events'),
    path('events/my/', views.user_events, name='user_events'),
    path('events/popular/', views.popular_events, name='popular_events'),

    # 当前用户的个人主页（不需要ID）
    path('profile/', views.own_profile, name='own_profile'),

    # 特定用户的个人主页（需要ID）
    path('profile/<int:user_id>/', views.profile, name='profile'),

    # 个人资料编辑页面（不需要ID）
    path('profile/edit/', views.profile_edit, name='profile_edit'),

    # 成绩
    path('grades/', views.my_grades, name='my_grades'),

    # 搜索
    path('search/', views.search, name='search'),

    # 忘记密码
    path('forgot-password/', views.forgot_password, name='forgot_password'),

    # 重置密码确认视图
    path('reset-password/<uidb64>/<token>/',
         views.CustomPasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),

    # 密码重置完成
    path('reset-password/complete/',
         views.password_reset_complete,
         name='password_reset_complete'),
]
