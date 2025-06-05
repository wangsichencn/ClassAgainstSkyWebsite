# core/admin.py

from django.contrib import admin
from .models import (
    AcademicGrade,  # 新名称
    Class,
    Course,
    CourseGrade,    # 新名称
    CourseSchedule,
    Material,
    AnnouncementCategory,
    Announcement,
    Post,
    Comment,
    Message,
    EventType,
    Event,
    EventRegistration  # 将EventSignup改为EventRegistration
)

# 取消注册旧模型（如果已注册）
# admin.site.unregister(Major)  # 如果已注册
# admin.site.unregister(Class)  # 如果已注册

# 注册所有模型
@admin.register(AcademicGrade)
class AcademicGradeAdmin(admin.ModelAdmin):
    list_display = ('name', 'academic_year')
    search_fields = ('name', 'academic_year')

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'grade', 'major')
    list_filter = ('grade', 'major')
    search_fields = ('name',)

# 确保只注册CourseGrade一次
@admin.register(CourseGrade)
class CourseGradeAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'score')
    list_filter = ('course',)
    search_fields = ('student__username', 'course__name')

# 注册EventRegistration
@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'registered_at')
    list_filter = ('event',)
    search_fields = ('user__username', 'event__title')


# 注册剩余模型...
admin.site.register(Course)
admin.site.register(CourseSchedule)
admin.site.register(Material)
admin.site.register(AnnouncementCategory)
admin.site.register(Announcement)
admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(Message)
admin.site.register(EventType)
admin.site.register(Event)