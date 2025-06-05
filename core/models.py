from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import datetime


# 专业
class Major(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


# 年级
class AcademicGrade(models.Model):
    name = models.CharField(max_length=50, unique=True)
    academic_year = models.CharField(max_length=9, default='2023-2024')  # 添加默认值

    def __str__(self):
        return self.name


# 班级
class Class(models.Model):
    name = models.CharField(max_length=100)
    grade = models.ForeignKey(
        AcademicGrade,
        on_delete=models.CASCADE,
        related_name='classes',
        default=1  # 保留默认值
    )
    major = models.ForeignKey(
        Major,
        on_delete=models.CASCADE,
        related_name='classes',
        default=1  # 添加专业默认值
    )

    def __str__(self):
        return f"{self.grade.name}{self.major.name}{self.name}班"


# 自定义用户，继承 AbstractUser
class User(AbstractUser):
    # 移除重复的 username 字段覆盖
    # （AbstractUser 已经定义了 username）
    # 添加班级归属
    class_belong = models.ForeignKey(
        Class,  # 指向 Class 模型
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        verbose_name='所属班级'
    )

    # 自定义字段
    student_id = models.CharField(
        '学号',
        max_length=20,
        unique=True,
        blank=False,
        null=False,
        help_text="必需：您的唯一学号"
    )
    email = models.EmailField(
        '邮箱地址',
        unique=True,
        blank=False,
        null=False,
        help_text="必需：您的有效邮箱地址"
    )
    full_name = models.CharField('真实姓名', max_length=100)
    nickname = models.CharField('昵称', max_length=50, blank=True)

    # 添加新字段
    avatar = models.ImageField('头像', upload_to='media/avatars/', blank=True, null=True)
    bio = models.TextField('个人简介', blank=True)
    join_date = models.DateField('加入日期', auto_now_add=True)
    is_teacher = models.BooleanField('教师身份', default=False)

    # 更新联系方式字段
    phone_number = models.CharField('手机号码', max_length=15, blank=True, default='')

    # 添加技能标签（多对多关系）
    skills = models.ManyToManyField('Skill', blank=True, verbose_name='技能标签')

    college = models.CharField('学院', max_length=100, blank=True, default='')
    class_name = models.CharField('班级', max_length=100, blank=True, default='')
    self_message = models.TextField('自我展示', blank=True, default='')

    # 可选：覆盖 __str__ 方法
    def __str__(self):
        return self.full_name if self.full_name else self.username


class Skill(models.Model):
    name = models.CharField('技能名称', max_length=50, unique=True)

    def __str__(self):
        return self.name

# 课程
class Course(models.Model):
    name = models.CharField('课程名称', max_length=100)
    code = models.CharField('课程代码', max_length=20, unique=True)
    instructor = models.CharField('授课教师', max_length=100, default='未知教师')
    semester = models.CharField('学期', max_length=20, default='2023-2024学年')
    class_belong = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='courses',
        verbose_name="开课班级",
        default=1  # 添加默认值
    )
    credit = models.PositiveSmallIntegerField('学分', default=2)

    def __str__(self):
        return f"{self.name} - {self.instructor}"


# 课表条目（课程安排）
class CourseSchedule(models.Model):
    WEEKDAY_CHOICES = [
        (1, '星期一'),
        (2, '星期二'),
        (3, '星期三'),
        (4, '星期四'),
        (5, '星期五'),
        (6, '星期六'),
        (7, '星期日')
    ]

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='schedules',
        default=1  # 添加默认值
    )
    weekday = models.IntegerField('星期几', choices=WEEKDAY_CHOICES, default=1)
    start_time = models.TimeField('开始时间', default=datetime.time(8, 0))
    end_time = models.TimeField('结束时间', default=datetime.time(10, 0))
    location = models.CharField('上课地点', max_length=100, default='未知教室')

    def __str__(self):
        return f"{self.course.name} - {self.get_weekday_display()} {self.start_time}-{self.end_time}"


# 课程资料
class Material(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='materials',
        default=1  # 添加默认值
    )
    title = models.CharField('资料标题', max_length=200, default='未命名资料')
    file = models.FileField('文件', upload_to='course_materials/')
    description = models.TextField('描述', blank=True, default='')
    uploaded_at = models.DateTimeField('上传时间', auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_materials',
        default=None  # 添加默认值
    )

    def __str__(self):
        return f"{self.course.name} - {self.title}"


# 成绩
class CourseGrade(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='grades',
        default=1  # 添加默认值
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='grades',
        default=1  # 添加默认值
    )
    score = models.DecimalField('分数', max_digits=5, decimal_places=2, default=60.0)
    exam_date = models.DateField('考试日期', null=True, blank=True, default=datetime.date.today)
    is_final = models.BooleanField('是否期末成绩', default=True)

    class Meta:
        unique_together = ('student', 'course', 'is_final')
        verbose_name = '成绩'
        verbose_name_plural = '成绩'

    def __str__(self):
        return f"{self.student} - {self.course.name}: {self.score}"


# 通知分类和通知模型
class AnnouncementCategory(models.Model):
    CATEGORY_CHOICES = [
        ('homework', '作业'),
        ('meeting', '会议'),
        ('survey', '调查'),
        ('activity', '活动'),
        ('academic', '学业'),
        ('other', '其他'),
    ]

    name = models.CharField('分类名称', max_length=20, unique=True, default='默认分类')
    slug = models.SlugField('标识符', max_length=20, choices=CATEGORY_CHOICES, unique=True, default='默认标识')
    color = models.CharField('颜色代码', max_length=7, default='#007bff')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '通知分类'
        verbose_name_plural = '通知分类'


# 添加新字段，修改现有的通知模型
class Announcement(models.Model):
    CATEGORY_CHOICES = [
        ('info', '一般信息'),
        ('warning', '重要通知'),
        ('event', '活动通知'),
        ('academic', '学业通知'),
        ('other', '其他'),
    ]

    SCOPE_CHOICES = [
        ('class', '班级'),
        ('grade', '年级'),
        ('major', '专业'),
        ('school', '全校'),
    ]

    title = models.CharField('标题', max_length=200)
    content = models.TextField('内容')
    # 改为使用选择字段而非外键
    category = models.CharField('分类', max_length=20, choices=CATEGORY_CHOICES, default='info')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,  # 改为级联删除
        related_name='authored_announcements'
    )
    scope = models.CharField('可见范围', max_length=10, choices=SCOPE_CHOICES, default='class')
    is_pinned = models.BooleanField('是否置顶', default=False)
    attachment = models.FileField('附件', upload_to='announcements/', blank=True, null=True)

    class_belong = models.ForeignKey(
        Class,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='announcements',
        verbose_name='所属班级'
    )

    class Meta:
        verbose_name = '通知'
        verbose_name_plural = '通知'
        ordering = ['-is_pinned', '-created_at']  # 置顶公告优先显示

    def __str__(self):
        return self.title

    # 添加方法获取分类和范围的显示文本
    def get_category_display_name(self):
        return dict(self.CATEGORY_CHOICES).get(self.category, self.category)

    def get_scope_display_name(self):
        return dict(self.SCOPE_CHOICES).get(self.scope, self.scope)


# 统一帖子模型
class Post(models.Model):
    VISIBILITY_CHOICES = [
        ('class', '班级'),
        ('grade', '年级'),
        ('major', '专业'),
        ('all', '全校'),
    ]

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='posts',
        default=1  # 添加默认值
    )
    title = models.CharField('标题', max_length=200, default='未命名帖子')
    content = models.TextField('内容', default='帖子内容')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    anonymous = models.BooleanField('匿名发表', default=False)
    visibility = models.CharField('可见范围', max_length=10, choices=VISIBILITY_CHOICES, default='class')

    attachment = models.FileField(
        '附件',
        upload_to='post_attachments/',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = '帖子'
        verbose_name_plural = '帖子'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


# 评论模型
class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments',
        default=1  # 添加默认值
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='comments',
        default=1  # 添加默认值
    )
    content = models.TextField('内容', default='评论内容')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    anonymous = models.BooleanField('匿名评论', default=False)

    class Meta:
        verbose_name = '评论'
        verbose_name_plural = '评论'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author}'s comment on {self.post.title}"


# 消息模型
class Message(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        default=1  # 添加默认值
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_messages',
        default=1  # 添加默认值
    )
    content = models.TextField('内容', default='消息内容')
    sent_at = models.DateTimeField('发送时间', auto_now_add=True)
    read = models.BooleanField('已读', default=False)
    visible_to_public = models.BooleanField(
        '公开展示',
        default=False,
        help_text='允许在接收者的个人主页上公开显示此消息'
    )

    def __str__(self):
        return f"Message from {self.sender} to {self.receiver}"


# 活动类型
class EventType(models.Model):
    name = models.CharField('类型名称', max_length=50, unique=True, default='默认活动类型')
    slug = models.SlugField('标识符', max_length=50, unique=True, default='default-event-type')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '活动类型'
        verbose_name_plural = '活动类型'


# 活动表
class Event(models.Model):
    # 替换原有的 event_type 字段定义
    EVENT_TYPE_CHOICES = [
        ('official', '正式活动'),
        ('casual', '随性邀请'),
    ]

    # 修改 event_type 字段定义
    event_type = models.CharField(
        '活动类型',
        max_length=20,
        choices=EVENT_TYPE_CHOICES,
        default='official'
    )

    VISIBILITY_CHOICES = [
        ('class', '班级'),
        ('grade', '年级'),
        ('major', '专业'),
        ('all', '全校'),
    ]

    title = models.CharField('标题', max_length=200, default='未命名活动')
    description = models.TextField('描述', default='活动描述')
    location = models.CharField('地点', max_length=200, blank=True, default='未知地点')
    start_time = models.DateTimeField('开始时间', default=datetime.datetime.now)
    end_time = models.DateTimeField('结束时间', default=datetime.datetime.now)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_events',
        default=1
    )
    visibility = models.CharField('可见范围', max_length=10, choices=VISIBILITY_CHOICES, default='class')
    capacity = models.PositiveIntegerField('参与人数限制', null=True, blank=True, default=100)

    # 修改为只使用 auto_now_add 和 auto_now
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '活动'
        verbose_name_plural = '活动'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


# 活动报名
class EventRegistration(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='registrations',
        default=1  # 添加默认值
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='event_registrations',
        default=1  # 添加默认值
    )
    registered_at = models.DateTimeField('报名时间', auto_now_add=True)

    class Meta:
        unique_together = ('event', 'user')
        verbose_name = '活动报名'
        verbose_name_plural = '活动报名'

    def __str__(self):
        return f"{self.user} 报名参加 {self.event.title}"