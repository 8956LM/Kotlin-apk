import os
import sqlite3
from datetime import datetime, timedelta
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import StringProperty, NumericProperty, ListProperty, ObjectProperty
from kivy_garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import pandas as pd
from kivy.core.window import Window

# 设置窗口大小（仅开发时使用）
Window.size = (400, 600)

# 自定义颜色
PRIMARY_COLOR = [0.2, 0.5, 0.8, 1]  # 蓝色主色调
SECONDARY_COLOR = [0.8, 0.2, 0.2, 1]  # 红色强调色
LIGHT_COLOR = [0.95, 0.95, 0.95, 1]  # 浅灰背景
DARK_COLOR = [0.1, 0.1, 0.1, 1]  # 深灰文本
HIGHLIGHT_COLOR = [0.4, 0.7, 0.4, 1]  # 绿色成功

# 自定义字体大小
TITLE_FONT = 24
HEADER_FONT = 18
BODY_FONT = 14
SMALL_FONT = 12


# 数据库初始化
def init_database():
    conn = sqlite3.connect('class_management.db')
    cursor = conn.cursor()

    # 创建学生表
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS students
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY,
                       name
                       TEXT
                       NOT
                       NULL,
                       phone
                       TEXT,
                       level
                       TEXT,
                       hourly_rate
                       REAL,
                       discount
                       REAL
                       DEFAULT
                       1.0,
                       created_at
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP
                   )
                   ''')

    # 创建课程记录表
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS lessons
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY,
                       student_id
                       INTEGER,
                       start_time
                       TIMESTAMP,
                       end_time
                       TIMESTAMP,
                       duration
                       REAL,
                       amount
                       REAL,
                       notes
                       TEXT,
                       created_at
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP,
                       FOREIGN
                       KEY
                   (
                       student_id
                   ) REFERENCES students
                   (
                       id
                   )
                       )
                   ''')

    conn.commit()
    conn.close()


# 数据访问层
class Database:
    def __init__(self, db_path='class_management.db'):
        self.db_path = db_path

    def execute(self, query, params=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        result = cursor.fetchall()
        conn.close()
        return result

    def add_student(self, name, phone, level, hourly_rate, discount=1.0):
        query = '''
                INSERT INTO students (name, phone, level, hourly_rate, discount)
                VALUES (?, ?, ?, ?, ?) \
                '''
        self.execute(query, (name, phone, level, hourly_rate, discount))

    def get_all_students(self):
        query = 'SELECT * FROM students ORDER BY name'
        return self.execute(query)

    def get_student(self, student_id):
        query = 'SELECT * FROM students WHERE id = ?'
        return self.execute(query, (student_id,))[0]

    def update_student(self, student_id, name, phone, level, hourly_rate, discount=1.0):
        query = '''
                UPDATE students
                SET name        = ?, \
                    phone       = ?, \
                    level       = ?, \
                    hourly_rate = ?, \
                    discount    = ?
                WHERE id = ? \
                '''
        self.execute(query, (name, phone, level, hourly_rate, discount, student_id))

    def delete_student(self, student_id):
        # 先删除关联的课程记录
        self.execute('DELETE FROM lessons WHERE student_id = ?', (student_id,))
        # 再删除学生
        self.execute('DELETE FROM students WHERE id = ?', (student_id,))

    def add_lesson(self, student_id, start_time, end_time, notes=""):
        # 计算时长（小时）
        duration = (end_time - start_time).total_seconds() / 3600

        # 获取学生的小时费率和折扣
        student = self.get_student(student_id)
        hourly_rate = student[4]  # 小时费率
        discount = student[5]  # 折扣

        # 计算金额
        amount = duration * hourly_rate * discount

        query = '''
                INSERT INTO lessons (student_id, start_time, end_time, duration, amount, notes)
                VALUES (?, ?, ?, ?, ?, ?) \
                '''
        self.execute(query, (student_id, start_time, end_time, duration, amount, notes))

    def get_student_lessons(self, student_id):
        query = '''
                SELECT l.id, l.start_time, l.end_time, l.duration, l.amount, l.notes
                FROM lessons l
                WHERE l.student_id = ?
                ORDER BY l.start_time DESC \
                '''
        return self.execute(query, (student_id,))

    def get_all_lessons(self):
        query = '''
                SELECT l.id, s.name, l.start_time, l.end_time, l.duration, l.amount, l.notes
                FROM lessons l
                         JOIN students s ON l.student_id = s.id
                ORDER BY l.start_time DESC \
                '''
        return self.execute(query)

    def get_student_summary(self, student_id):
        query = '''
                SELECT COUNT(*), SUM(duration), SUM(amount)
                FROM lessons
                WHERE student_id = ? \
                '''
        return self.execute(query, (student_id,))[0]

    def get_monthly_summary(self, year, month):
        query = '''
                SELECT strftime('%Y-%m-%d', start_time) as date, 
               SUM(duration) as total_duration, 
               SUM(amount) as total_amount
                FROM lessons
                WHERE strftime('%Y', start_time) = ? AND strftime('%m', start_time) = ?
                GROUP BY date
                ORDER BY date \
                '''
        return self.execute(query, (str(year), f"{month:02d}"))

    def get_student_id_by_name(self, name):
        query = 'SELECT id FROM students WHERE name = ?'
        result = self.execute(query, (name,))
        if result:
            return result[0][0]
        return None


# 自定义组件
class RoundedButton(Button):
    def __init__(self, **kwargs):
        super(RoundedButton, self).__init__(**kwargs)
        self.background_normal = ''
        self.background_color = PRIMARY_COLOR
        self.border_radius = [10]
        self.size_hint_y = None
        self.height = dp(48)
        self.font_size = BODY_FONT
        self.color = LIGHT_COLOR


class RoundedTextField(TextInput):
    def __init__(self, **kwargs):
        super(RoundedTextField, self).__init__(**kwargs)
        self.background_normal = ''
        self.background_color = LIGHT_COLOR
        self.border_radius = [8]
        self.size_hint_y = None
        self.height = dp(40)
        self.font_size = BODY_FONT
        self.padding = [dp(12), dp(10)]


class RoundedSpinner(Spinner):
    def __init__(self, **kwargs):
        super(RoundedSpinner, self).__init__(**kwargs)
        self.background_normal = ''
        self.background_color = LIGHT_COLOR
        self.border_radius = [8]
        self.size_hint_y = None
        self.height = dp(40)
        self.font_size = BODY_FONT
        self.padding = [dp(12), dp(10)]
        self.color = DARK_COLOR


class CustomLabel(Label):
    def __init__(self, **kwargs):
        super(CustomLabel, self).__init__(**kwargs)
        self.font_size = BODY_FONT
        self.color = DARK_COLOR
        self.halign = 'left'
        self.valign = 'middle'
        self.size_hint_y = None
        self.height = dp(40)


class HeaderLabel(Label):
    def __init__(self, **kwargs):
        super(HeaderLabel, self).__init__(**kwargs)
        self.font_size = HEADER_FONT
        self.color = DARK_COLOR
        self.bold = True
        self.halign = 'left'
        self.valign = 'middle'
        self.size_hint_y = None
        self.height = dp(50)


class TitleLabel(Label):
    def __init__(self, **kwargs):
        super(TitleLabel, self).__init__(**kwargs)
        self.font_size = TITLE_FONT
        self.color = DARK_COLOR
        self.bold = True
        self.halign = 'center'
        self.valign = 'middle'
        self.size_hint_y = None
        self.height = dp(60)


# 主屏幕
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.db = Database()
        self.layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(20))
        self.layout.background_color = LIGHT_COLOR

        # 标题
        self.title = TitleLabel(text='上课管理系统')
        self.layout.add_widget(self.title)

        # 欢迎信息
        self.welcome = CustomLabel(
            text='欢迎使用上课管理系统\n请选择您要进行的操作',
            font_size=HEADER_FONT,
            halign='center',
            valign='middle',
            size_hint_y=0.2
        )
        self.layout.add_widget(self.welcome)

        # 按钮区域
        self.button_layout = BoxLayout(orientation='vertical', size_hint=(1, 0.5), spacing=dp(15))

        self.students_btn = RoundedButton(text='学生管理', font_size=HEADER_FONT)
        self.students_btn.bind(on_press=self.go_to_students)

        self.lessons_btn = RoundedButton(text='课程记录', font_size=HEADER_FONT)
        self.lessons_btn.bind(on_press=self.go_to_lessons)

        self.stats_btn = RoundedButton(text='统计报表', font_size=HEADER_FONT)
        self.stats_btn.bind(on_press=self.go_to_stats)

        self.button_layout.add_widget(self.students_btn)
        self.button_layout.add_widget(self.lessons_btn)
        self.button_layout.add_widget(self.stats_btn)

        self.layout.add_widget(self.button_layout)

        # 底部信息
        self.footer = CustomLabel(
            text=f'版本 1.0.0\n当前时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
            font_size=SMALL_FONT,
            halign='center',
            valign='middle',
            size_hint_y=0.1
        )
        self.layout.add_widget(self.footer)

        self.add_widget(self.layout)

    def go_to_students(self, instance):
        self.manager.transition = SlideTransition(direction='left')
        self.manager.current = 'students'

    def go_to_lessons(self, instance):
        self.manager.transition = SlideTransition(direction='left')
        self.manager.current = 'lessons'

    def go_to_stats(self, instance):
        self.manager.transition = SlideTransition(direction='left')
        self.manager.current = 'stats'


# 学生管理屏幕
class StudentsScreen(Screen):
    def __init__(self, **kwargs):
        super(StudentsScreen, self).__init__(**kwargs)
        self.db = Database()
        self.layout = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(15))

        # 顶部导航栏
        self.header = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(60))

        self.back_btn = Button(
            text='◀',
            size_hint=(0.1, 1),
            background_normal='',
            background_color=[0, 0, 0, 0],
            color=DARK_COLOR,
            font_size=HEADER_FONT
        )
        self.back_btn.bind(on_press=self.go_back)

        self.title = HeaderLabel(text='学生管理', size_hint=(0.8, 1), halign='center')

        self.header.add_widget(self.back_btn)
        self.header.add_widget(self.title)

        self.layout.add_widget(self.header)

        # 添加学生按钮
        self.add_student_btn = RoundedButton(text='+ 添加学生')
        self.add_student_btn.bind(on_press=self.show_add_student)
        self.layout.add_widget(self.add_student_btn)

        # 学生列表
        self.students_layout = BoxLayout(orientation='vertical', size_hint=(1, 1))

        # 列表头部
        self.list_header = GridLayout(cols=5, size_hint=(1, None), height=dp(40))
        self.list_header.padding = [dp(10), 0]
        self.list_header.spacing = [dp(5), 0]

        headers = ['姓名', '电话', '级别', '费率', '操作']
        for header in headers:
            label = HeaderLabel(text=header, size_hint=(None, 1), width=dp(60))
            if header == '姓名':
                label.width = dp(100)
            if header == '操作':
                label.width = dp(120)
            self.list_header.add_widget(label)

        self.students_layout.add_widget(self.list_header)

        # 学生内容区域
        self.students_content = ScrollView(size_hint=(1, 1))
        self.students_grid = GridLayout(cols=5, size_hint_y=None, padding=[dp(10), 0], spacing=[dp(5), dp(5)])
        self.students_grid.bind(minimum_height=self.students_grid.setter('height'))

        self.students_content.add_widget(self.students_grid)
        self.students_layout.add_widget(self.students_content)

        self.layout.add_widget(self.students_layout)

        self.add_widget(self.layout)

    def on_enter(self):
        # 刷新学生列表
        self.load_students()

    def load_students(self):
        # 清空现有学生
        self.students_grid.clear_widgets()

        # 加载学生数据
        students = self.db.get_all_students()
        for student in students:
            student_id = student[0]
            name = student[1]
            phone = student[2]
            level = student[3]
            hourly_rate = student[4]
            discount = student[5]

            # 为每个学生创建一行
            row_layout = GridLayout(cols=5, size_hint_y=None, height=dp(50))
            row_layout.padding = [dp(5), 0]
            row_layout.spacing = [dp(5), 0]

            # 学生信息
            row_layout.add_widget(CustomLabel(text=name, size_hint=(None, 1), width=dp(100)))
            row_layout.add_widget(CustomLabel(text=phone, size_hint=(None, 1), width=dp(60)))
            row_layout.add_widget(CustomLabel(text=level, size_hint=(None, 1), width=dp(60)))
            row_layout.add_widget(CustomLabel(text=f"{hourly_rate:.2f}", size_hint=(None, 1), width=dp(60)))

            # 操作按钮
            actions_layout = BoxLayout(orientation='horizontal', size_hint=(None, 1), width=dp(120))

            edit_btn = Button(
                text='编辑',
                size_hint=(0.5, 1),
                background_normal='',
                background_color=PRIMARY_COLOR,
                color=LIGHT_COLOR,
                font_size=SMALL_FONT,
                border_radius=[5]
            )
            edit_btn.bind(on_press=lambda instance, sid=student_id: self.show_edit_student(sid))

            delete_btn = Button(
                text='删除',
                size_hint=(0.5, 1),
                background_normal='',
                background_color=SECONDARY_COLOR,
                color=LIGHT_COLOR,
                font_size=SMALL_FONT,
                border_radius=[5]
            )
            delete_btn.bind(on_press=lambda instance, sid=student_id: self.delete_student(sid))

            actions_layout.add_widget(edit_btn)
            actions_layout.add_widget(delete_btn)

            row_layout.add_widget(actions_layout)

            self.students_grid.add_widget(row_layout)

    def show_add_student(self, instance):
        # 创建添加学生的弹出窗口
        popup_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))

        # 标题
        popup_layout.add_widget(HeaderLabel(text='添加学生', size_hint_y=None, height=dp(50), halign='center'))

        # 输入字段
        form_layout = GridLayout(cols=2, size_hint_y=None, height=dp(200), spacing=dp(10))

        form_layout.add_widget(CustomLabel(text='姓名:', size_hint_y=None, height=dp(40)))
        name_input = RoundedTextField(hint_text='必填')

        form_layout.add_widget(CustomLabel(text='电话:', size_hint_y=None, height=dp(40)))
        phone_input = RoundedTextField()

        form_layout.add_widget(CustomLabel(text='级别:', size_hint_y=None, height=dp(40)))
        level_input = RoundedTextField()

        form_layout.add_widget(CustomLabel(text='小时费率:', size_hint_y=None, height=dp(40)))
        rate_input = RoundedTextField(hint_text='必填', input_filter='float')

        form_layout.add_widget(CustomLabel(text='折扣:', size_hint_y=None, height=dp(40)))
        discount_input = RoundedTextField(text='1.0', input_filter='float')

        form_layout.add_widget(Label(size_hint_y=None, height=dp(40)))  # 占位

        form_layout.add_widget(name_input)
        form_layout.add_widget(phone_input)
        form_layout.add_widget(level_input)
        form_layout.add_widget(rate_input)
        form_layout.add_widget(discount_input)

        popup_layout.add_widget(form_layout)

        # 按钮
        buttons_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(15))

        save_btn = RoundedButton(text='保存')
        save_btn.bind(on_press=lambda instance: self.save_student(
            name_input.text, phone_input.text, level_input.text, rate_input.text, discount_input.text, popup))

        cancel_btn = RoundedButton(text='取消', background_color=[0.5, 0.5, 0.5, 1])
        cancel_btn.bind(on_press=lambda instance: popup.dismiss())

        buttons_layout.add_widget(save_btn)
        buttons_layout.add_widget(cancel_btn)

        popup_layout.add_widget(buttons_layout)

        popup = Popup(
            title='',
            content=popup_layout,
            size_hint=(0.9, 0.7),
            auto_dismiss=False,
            background_color=[0, 0, 0, 0.5],
            separator_height=0
        )
        popup.open()

    def show_edit_student(self, student_id):
        student = self.db.get_student(student_id)

        # 创建编辑学生的弹出窗口
        popup_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))

        # 标题
        popup_layout.add_widget(HeaderLabel(text='编辑学生', size_hint_y=None, height=dp(50), halign='center'))

        # 输入字段
        form_layout = GridLayout(cols=2, size_hint_y=None, height=dp(200), spacing=dp(10))

        form_layout.add_widget(CustomLabel(text='姓名:', size_hint_y=None, height=dp(40)))
        name_input = RoundedTextField(text=student[1])

        form_layout.add_widget(CustomLabel(text='电话:', size_hint_y=None, height=dp(40)))
        phone_input = RoundedTextField(text=student[2])

        form_layout.add_widget(CustomLabel(text='级别:', size_hint_y=None, height=dp(40)))
        level_input = RoundedTextField(text=student[3])

        form_layout.add_widget(CustomLabel(text='小时费率:', size_hint_y=None, height=dp(40)))
        rate_input = RoundedTextField(text=str(student[4]), input_filter='float')

        form_layout.add_widget(CustomLabel(text='折扣:', size_hint_y=None, height=dp(40)))
        discount_input = RoundedTextField(text=str(student[5]), input_filter='float')

        form_layout.add_widget(Label(size_hint_y=None, height=dp(40)))  # 占位

        form_layout.add_widget(name_input)
        form_layout.add_widget(phone_input)
        form_layout.add_widget(level_input)
        form_layout.add_widget(rate_input)
        form_layout.add_widget(discount_input)

        popup_layout.add_widget(form_layout)

        # 按钮
        buttons_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(15))

        save_btn = RoundedButton(text='保存')
        save_btn.bind(on_press=lambda instance: self.update_student(
            student_id, name_input.text, phone_input.text, level_input.text, rate_input.text, discount_input.text,
            popup))

        cancel_btn = RoundedButton(text='取消', background_color=[0.5, 0.5, 0.5, 1])
        cancel_btn.bind(on_press=lambda instance: popup.dismiss())

        buttons_layout.add_widget(save_btn)
        buttons_layout.add_widget(cancel_btn)

        popup_layout.add_widget(buttons_layout)

        popup = Popup(
            title='',
            content=popup_layout,
            size_hint=(0.9, 0.7),
            auto_dismiss=False,
            background_color=[0, 0, 0, 0.5],
            separator_height=0
        )
        popup.open()

    def save_student(self, name, phone, level, rate, discount, popup):
        if not name or not rate:
            self.show_message('错误', '姓名和小时费率不能为空')
            return

        try:
            hourly_rate = float(rate)
            discount_value = float(discount)
            self.db.add_student(name, phone, level, hourly_rate, discount_value)
            popup.dismiss()
            self.load_students()
            self.show_message('成功', '学生添加成功')
        except ValueError:
            self.show_message('错误', '小时费率和折扣必须是数字')

    def update_student(self, student_id, name, phone, level, rate, discount, popup):
        if not name or not rate:
            self.show_message('错误', '姓名和小时费率不能为空')
            return

        try:
            hourly_rate = float(rate)
            discount_value = float(discount)
            self.db.update_student(student_id, name, phone, level, hourly_rate, discount_value)
            popup.dismiss()
            self.load_students()
            self.show_message('成功', '学生信息更新成功')
        except ValueError:
            self.show_message('错误', '小时费率和折扣必须是数字')

    def delete_student(self, student_id):
        popup_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))

        message = CustomLabel(
            text='确定要删除该学生吗？\n这将删除该学生的所有课程记录。',
            size_hint_y=None,
            height=dp(80),
            halign='center',
            valign='middle'
        )

        buttons_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(15))

        confirm_btn = RoundedButton(text='确定', background_color=SECONDARY_COLOR)
        confirm_btn.bind(on_press=lambda instance: self.confirm_delete(student_id, popup))

        cancel_btn = RoundedButton(text='取消', background_color=[0.5, 0.5, 0.5, 1])
        cancel_btn.bind(on_press=lambda instance: popup.dismiss())

        buttons_layout.add_widget(confirm_btn)
        buttons_layout.add_widget(cancel_btn)

        popup_layout.add_widget(message)
        popup_layout.add_widget(buttons_layout)

        popup = Popup(
            title='确认删除',
            content=popup_layout,
            size_hint=(0.7, 0.4),
            auto_dismiss=False,
            background_color=[0, 0, 0, 0.5]
        )
        popup.open()

    def confirm_delete(self, student_id, popup):
        self.db.delete_student(student_id)
        popup.dismiss()
        self.load_students()
        self.show_message('成功', '学生已删除')

    def go_back(self, instance):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'main'

    def show_message(self, title, message):
        popup_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))

        message_label = CustomLabel(
            text=message,
            size_hint_y=None,
            height=dp(80),
            halign='center',
            valign='middle'
        )

        ok_btn = RoundedButton(text='确定')
        ok_btn.bind(on_press=lambda instance: popup.dismiss())

        popup_layout.add_widget(message_label)
        popup_layout.add_widget(ok_btn)

        popup = Popup(
            title=title,
            content=popup_layout,
            size_hint=(0.7, 0.3),
            auto_dismiss=False,
            background_color=[0, 0, 0, 0.5]
        )
        popup.open()


# 课程记录屏幕
class LessonsScreen(Screen):
    def __init__(self, **kwargs):
        super(LessonsScreen, self).__init__(**kwargs)
        self.db = Database()
        self.layout = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(15))

        # 顶部导航栏
        self.header = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(60))

        self.back_btn = Button(
            text='◀',
            size_hint=(0.1, 1),
            background_normal='',
            background_color=[0, 0, 0, 0],
            color=DARK_COLOR,
            font_size=HEADER_FONT
        )
        self.back_btn.bind(on_press=self.go_back)

        self.title = HeaderLabel(text='课程记录', size_hint=(0.8, 1), halign='center')

        self.header.add_widget(self.back_btn)
        self.header.add_widget(self.title)

        self.layout.add_widget(self.header)

        # 筛选区域
        self.filter_layout = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(50), spacing=dp(10))

        self.filter_layout.add_widget(CustomLabel(text='学生:', size_hint=(0.2, 1), halign='right'))

        self.student_spinner = RoundedSpinner(
            text='选择学生',
            values=['选择学生'],
            size_hint=(0.5, 1)
        )
        self.student_spinner.bind(text=self.filter_by_student)

        self.add_lesson_btn = RoundedButton(text='+ 添加记录', size_hint=(0.3, 1))
        self.add_lesson_btn.bind(on_press=self.show_add_lesson)

        self.filter_layout.add_widget(self.student_spinner)
        self.filter_layout.add_widget(self.add_lesson_btn)

        self.layout.add_widget(self.filter_layout)

        # 课程记录列表
        self.lessons_layout = BoxLayout(orientation='vertical', size_hint=(1, 1))

        # 列表头部
        self.list_header = GridLayout(cols=6, size_hint=(1, None), height=dp(40))
        self.list_header.padding = [dp(10), 0]
        self.list_header.spacing = [dp(5), 0]

        headers = ['学生', '开始时间', '结束时间', '时长', '金额', '操作']
        for header in headers:
            label = HeaderLabel(text=header, size_hint=(None, 1), width=dp(50))
            if header == '学生':
                label.width = dp(80)
            if header == '开始时间' or header == '结束时间':
                label.width = dp(80)
            if header == '操作':
                label.width = dp(60)
            self.list_header.add_widget(label)

        self.lessons_layout.add_widget(self.list_header)

        # 课程内容区域
        self.lessons_content = ScrollView(size_hint=(1, 1))
        self.lessons_grid = GridLayout(cols=6, size_hint_y=None, padding=[dp(10), 0], spacing=[dp(5), dp(5)])
        self.lessons_grid.bind(minimum_height=self.lessons_grid.setter('height'))

        self.lessons_content.add_widget(self.lessons_grid)
        self.lessons_layout.add_widget(self.lessons_content)

        self.layout.add_widget(self.lessons_layout)

        self.add_widget(self.layout)

    def on_enter(self):
        # 刷新学生下拉列表
        students = self.db.get_all_students()
        self.student_spinner.values = ['选择学生'] + [student[1] for student in students]

        # 默认加载所有课程记录
        self.load_lessons()

    def load_lessons(self, student_id=None):
        # 清空现有记录
        self.lessons_grid.clear_widgets()

        # 加载课程记录
        if student_id:
            lessons = self.db.get_student_lessons(student_id)
            # 获取学生姓名
            student = self.db.get_student(student_id)
            student_name = student[1]

            for lesson in lessons:
                lesson_id = lesson[0]
                start_time = lesson[1]
                end_time = lesson[2]
                duration = lesson[3]
                amount = lesson[4]
                notes = lesson[5]

                # 为每个课程创建一行
                row_layout = GridLayout(cols=6, size_hint_y=None, height=dp(50))
                row_layout.padding = [dp(5), 0]
                row_layout.spacing = [dp(5), 0]

                # 课程信息
                row_layout.add_widget(CustomLabel(text=student_name, size_hint=(None, 1), width=dp(80)))
                row_layout.add_widget(CustomLabel(text=start_time.split(' ')[1], size_hint=(None, 1), width=dp(80)))
                row_layout.add_widget(CustomLabel(text=end_time.split(' ')[1], size_hint=(None, 1), width=dp(80)))
                row_layout.add_widget(CustomLabel(text=f"{duration:.2f}", size_hint=(None, 1), width=dp(50)))
                row_layout.add_widget(CustomLabel(text=f"¥{amount:.2f}", size_hint=(None, 1), width=dp(50)))

                # 操作按钮
                actions_layout = BoxLayout(orientation='horizontal', size_hint=(None, 1), width=dp(60))

                delete_btn = Button(
                    text='删除',
                    size_hint=(1, 1),
                    background_normal='',
                    background_color=SECONDARY_COLOR,
                    color=LIGHT_COLOR,
                    font_size=SMALL_FONT,
                    border_radius=[5]
                )
                delete_btn.bind(on_press=lambda instance, lid=lesson_id: self.delete_lesson(lid))

                actions_layout.add_widget(delete_btn)

                row_layout.add_widget(actions_layout)

                self.lessons_grid.add_widget(row_layout)
        else:
            lessons = self.db.get_all_lessons()
            for lesson in lessons:
                lesson_id = lesson[0]
                student_name = lesson[1]
                start_time = lesson[2]
                end_time = lesson[3]
                duration = lesson[4]
                amount = lesson[5]
                notes = lesson[6]

                # 为每个课程创建一行
                row_layout = GridLayout(cols=6, size_hint_y=None, height=dp(50))
                row_layout.padding = [dp(5), 0]
                row_layout.spacing = [dp(5), 0]

                # 课程信息
                row_layout.add_widget(CustomLabel(text=student_name, size_hint=(None, 1), width=dp(80)))
                row_layout.add_widget(CustomLabel(text=start_time.split(' ')[1], size_hint=(None, 1), width=dp(80)))
                row_layout.add_widget(CustomLabel(text=end_time.split(' ')[1], size_hint=(None, 1), width=dp(80)))
                row_layout.add_widget(CustomLabel(text=f"{duration:.2f}", size_hint=(None, 1), width=dp(50)))
                row_layout.add_widget(CustomLabel(text=f"¥{amount:.2f}", size_hint=(None, 1), width=dp(50)))

                # 操作按钮
                actions_layout = BoxLayout(orientation='horizontal', size_hint=(None, 1), width=dp(60))

                delete_btn = Button(
                    text='删除',
                    size_hint=(1, 1),
                    background_normal='',
                    background_color=SECONDARY_COLOR,
                    color=LIGHT_COLOR,
                    font_size=SMALL_FONT,
                    border_radius=[5]
                )
                delete_btn.bind(on_press=lambda instance, lid=lesson_id: self.delete_lesson(lid))

                actions_layout.add_widget(delete_btn)

                row_layout.add_widget(actions_layout)

                self.lessons_grid.add_widget(row_layout)

                def filter_by_student(self, instance, value):
                    if value == '选择学生':
                        self.load_lessons()
                    else:
                        # 获取学生ID
                        student_id = self.db.get_student_id_by_name(value)
                        if student_id:
                            self.load_lessons(student_id)
                        else:
                            self.show_message('错误', '未找到该学生')

                def show_add_lesson(self, instance):
                    # 创建添加课程记录的弹出窗口
                    popup_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))

                    # 标题
                    popup_layout.add_widget(
                        HeaderLabel(text='添加课程记录', size_hint_y=None, height=dp(50), halign='center'))

                    # 表单区域
                    form_layout = GridLayout(cols=2, size_hint_y=None, height=dp(280), spacing=dp(10))

                    # 学生选择
                    form_layout.add_widget(CustomLabel(text='学生:', size_hint_y=None, height=dp(40)))
                    student_spinner = RoundedSpinner(
                        text='选择学生',
                        values=[student[1] for student in self.db.get_all_students()],
                        size_hint_y=None,
                        height=dp(40)
                    )

                    # 开始时间选择
                    from kivy.uix.picker import DateTimePicker
                    form_layout.add_widget(CustomLabel(text='开始时间:', size_hint_y=None, height=dp(40)))
                    start_time_picker = DateTimePicker(mode='spinner', size_hint_y=None, height=dp(40))

                    # 设置默认开始时间（当前时间）
                    now = datetime.now()
                    start_time_picker.datetime = now

                    # 结束时间选择
                    form_layout.add_widget(CustomLabel(text='结束时间:', size_hint_y=None, height=dp(40)))
                    end_time_picker = DateTimePicker(mode='spinner', size_hint_y=None, height=dp(40))

                    # 设置默认结束时间（当前时间 + 1小时）
                    end_time_picker.datetime = now + timedelta(hours=1)

                    # 备注
                    form_layout.add_widget(CustomLabel(text='备注:', size_hint_y=None, height=dp(40)))
                    notes_input = RoundedTextField(multiline=True, size_hint_y=None, height=dp(80))

                    form_layout.add_widget(student_spinner)
                    form_layout.add_widget(start_time_picker)
                    form_layout.add_widget(end_time_picker)
                    form_layout.add_widget(notes_input)

                    popup_layout.add_widget(form_layout)

                    # 按钮
                    buttons_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50),
                                               spacing=dp(15))

                    save_btn = RoundedButton(text='保存')
                    save_btn.bind(on_press=lambda instance: self.save_lesson(
                        student_spinner.text, start_time_picker.datetime, end_time_picker.datetime,
                        notes_input.text, popup))

                    cancel_btn = RoundedButton(text='取消', background_color=[0.5, 0.5, 0.5, 1])
                    cancel_btn.bind(on_press=lambda instance: popup.dismiss())

                    buttons_layout.add_widget(save_btn)
                    buttons_layout.add_widget(cancel_btn)

                    popup_layout.add_widget(buttons_layout)

                    popup = Popup(
                        title='',
                        content=popup_layout,
                        size_hint=(0.9, 0.8),
                        auto_dismiss=False,
                        background_color=[0, 0, 0, 0.5],
                        separator_height=0
                    )
                    popup.open()

                def save_lesson(self, student_name, start_time, end_time, notes, popup):
                    if student_name == '选择学生':
                        self.show_message('错误', '请选择学生')
                        return

                    if start_time >= end_time:
                        self.show_message('错误', '结束时间必须晚于开始时间')
                        return

                    # 获取学生ID
                    student_id = self.db.get_student_id_by_name(student_name)
                    if student_id:
                        self.db.add_lesson(student_id, start_time, end_time, notes)
                        popup.dismiss()
                        self.load_lessons()
                        self.show_message('成功', '课程记录添加成功')
                    else:
                        self.show_message('错误', '学生不存在')

                def delete_lesson(self, lesson_id):
                    popup_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))

                    message = CustomLabel(
                        text='确定要删除该课程记录吗？',
                        size_hint_y=None,
                        height=dp(80),
                        halign='center',
                        valign='middle'
                    )

                    buttons_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50),
                                               spacing=dp(15))

                    confirm_btn = RoundedButton(text='确定', background_color=SECONDARY_COLOR)
                    confirm_btn.bind(on_press=lambda instance: self.confirm_delete(lesson_id, popup))

                    cancel_btn = RoundedButton(text='取消', background_color=[0.5, 0.5, 0.5, 1])
                    cancel_btn.bind(on_press=lambda instance: popup.dismiss())

                    buttons_layout.add_widget(confirm_btn)
                    buttons_layout.add_widget(cancel_btn)

                    popup_layout.add_widget(message)
                    popup_layout.add_widget(buttons_layout)

                    popup = Popup(
                        title='确认删除',
                        content=popup_layout,
                        size_hint=(0.7, 0.4),
                        auto_dismiss=False,
                        background_color=[0, 0, 0, 0.5]
                    )
                    popup.open()

                def confirm_delete(self, lesson_id, popup):
                    self.db.execute('DELETE FROM lessons WHERE id = ?', (lesson_id,))
                    popup.dismiss()
                    self.load_lessons()
                    self.show_message('成功', '课程记录已删除')

                def go_back(self, instance):
                    self.manager.transition = SlideTransition(direction='right')
                    self.manager.current = 'main'

                def show_message(self, title, message):
                    popup_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))

                    message_label = CustomLabel(
                        text=message,
                        size_hint_y=None,
                        height=dp(80),
                        halign='center',
                        valign='middle'
                    )

                    ok_btn = RoundedButton(text='确定')
                    ok_btn.bind(on_press=lambda instance: popup.dismiss())

                    popup_layout.add_widget(message_label)
                    popup_layout.add_widget(ok_btn)

                    popup = Popup(
                        title=title,
                        content=popup_layout,
                        size_hint=(0.7, 0.3),
                        auto_dismiss=False,
                        background_color=[0, 0, 0, 0.5]
                    )
                    popup.open()

                # 统计报表屏幕
                class StatsScreen(Screen):
                    def __init__(self, **kwargs):
                        super(StatsScreen, self).__init__(**kwargs)
                        self.db = Database()
                        self.layout = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(15))

                        # 顶部导航栏
                        self.header = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(60))

                        self.back_btn = Button(
                            text='◀',
                            size_hint=(0.1, 1),
                            background_normal='',
                            background_color=[0, 0, 0, 0],
                            color=DARK_COLOR,
                            font_size=HEADER_FONT
                        )
                        self.back_btn.bind(on_press=self.go_back)

                        self.title = HeaderLabel(text='统计报表', size_hint=(0.8, 1), halign='center')

                        self.header.add_widget(self.back_btn)
                        self.header.add_widget(self.title)

                        self.layout.add_widget(self.header)

                        # 筛选区域
                        self.filter_layout = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(50),
                                                       spacing=dp(10))

                        self.filter_layout.add_widget(CustomLabel(text='学生:', size_hint=(0.2, 1), halign='right'))

                        self.student_spinner = RoundedSpinner(
                            text='选择学生',
                            values=['选择学生'],
                            size_hint=(0.5, 1)
                        )
                        self.student_spinner.bind(text=self.filter_by_student)

                        self.export_btn = RoundedButton(text='导出数据', size_hint=(0.3, 1))
                        self.export_btn.bind(on_press=self.export_data)

                        self.filter_layout.add_widget(self.student_spinner)
                        self.filter_layout.add_widget(self.export_btn)

                        self.layout.add_widget(self.filter_layout)

                        # 统计信息区域
                        self.stats_layout = BoxLayout(orientation='vertical', size_hint=(1, 1))

                        # 统计摘要
                        self.summary_layout = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(100),
                                                        spacing=dp(15))

                        # 总课程数卡片
                        self.lessons_card = BoxLayout(orientation='vertical', size_hint=(1 / 3, 1), padding=dp(10))
                        self.lessons_card.background_color = [0.9, 0.9, 0.9, 1]
                        self.lessons_card.border_radius = [10]

                        self.lessons_card.add_widget(
                            CustomLabel(text='总课程数', size_hint_y=None, height=dp(30), halign='center'))
                        self.total_lessons_label = Label(text='0', font_size=TITLE_FONT, color=DARK_COLOR,
                                                         halign='center', valign='middle')
                        self.lessons_card.add_widget(self.total_lessons_label)

                        # 总时长卡片
                        self.hours_card = BoxLayout(orientation='vertical', size_hint=(1 / 3, 1), padding=dp(10))
                        self.hours_card.background_color = [0.9, 0.9, 0.9, 1]
                        self.hours_card.border_radius = [10]

                        self.hours_card.add_widget(
                            CustomLabel(text='总时长(小时)', size_hint_y=None, height=dp(30), halign='center'))
                        self.total_hours_label = Label(text='0', font_size=TITLE_FONT, color=DARK_COLOR,
                                                       halign='center', valign='middle')
                        self.hours_card.add_widget(self.total_hours_label)

                        # 总金额卡片
                        self.amount_card = BoxLayout(orientation='vertical', size_hint=(1 / 3, 1), padding=dp(10))
                        self.amount_card.background_color = [0.9, 0.9, 0.9, 1]
                        self.amount_card.border_radius = [10]

                        self.amount_card.add_widget(
                            CustomLabel(text='总金额(元)', size_hint_y=None, height=dp(30), halign='center'))
                        self.total_amount_label = Label(text='¥0.00', font_size=TITLE_FONT, color=DARK_COLOR,
                                                        halign='center', valign='middle')
                        self.amount_card.add_widget(self.total_amount_label)

                        self.summary_layout.add_widget(self.lessons_card)
                        self.summary_layout.add_widget(self.hours_card)
                        self.summary_layout.add_widget(self.amount_card)

                        self.stats_layout.add_widget(self.summary_layout)

                        # 图表区域
                        self.chart_layout = BoxLayout(orientation='vertical', size_hint=(1, 1), padding=dp(10))

                        # 图表将在on_enter中动态创建

                        self.stats_layout.add_widget(self.chart_layout)

                        self.layout.add_widget(self.stats_layout)

                        self.add_widget(self.layout)

                    def on_enter(self):
                        # 刷新学生下拉列表
                        students = self.db.get_all_students()
                        self.student_spinner.values = ['选择学生'] + [student[1] for student in students]

                        # 加载统计数据
                        self.load_stats()

                    def load_stats(self, student_id=None):
                        # 清除现有图表
                        for child in self.chart_layout.children[:]:
                            self.chart_layout.remove_widget(child)

                        # 计算统计数据
                        if student_id:
                            # 学生统计
                            summary = self.db.get_student_summary(student_id)
                            student = self.db.get_student(student_id)
                            student_name = student[1]

                            self.total_lessons_label.text = str(summary[0])
                            self.total_hours_label.text = f"{summary[1]:.2f}"
                            self.total_amount_label.text = f"¥{summary[2]:.2f}"

                            # 创建图表
                            self.create_student_chart(student_id, student_name)
                        else:
                            # 总体统计
                            lessons = self.db.get_all_lessons()
                            total_lessons = len(lessons)
                            total_hours = sum([lesson[4] for lesson in lessons])
                            total_amount = sum([lesson[5] for lesson in lessons])

                            self.total_lessons_label.text = str(total_lessons)
                            self.total_hours_label.text = f"{total_hours:.2f}"
                            self.total_amount_label.text = f"¥{total_amount:.2f}"

                            # 创建图表
                            self.create_overall_chart()

                    def create_student_chart(self, student_id, student_name):
                        # 获取学生课程记录
                        lessons = self.db.get_student_lessons(student_id)

                        if not lessons:
                            self.chart_layout.add_widget(
                                CustomLabel(
                                    text='没有课程记录可供显示',
                                    size_hint=(1, 1),
                                    halign='center',
                                    valign='middle',
                                    font_size=HEADER_FONT
                                )
                            )
                            return

                        # 按日期分组
                        from collections import defaultdict
                        daily_data = defaultdict(lambda: {'lessons': 0, 'hours': 0, 'amount': 0})

                        for lesson in lessons:
                            date_str = lesson[1].split(' ')[0]  # 获取日期部分
                            daily_data[date_str]['lessons'] += 1
                            daily_data[date_str]['hours'] += lesson[3]
                            daily_data[date_str]['amount'] += lesson[4]

                        # 排序日期
                        sorted_dates = sorted(daily_data.keys())

                        # 准备数据
                        dates = [datetime.strptime(date, '%Y-%m-%d') for date in sorted_dates]
                        hours = [daily_data[date]['hours'] for date in sorted_dates]
                        amounts = [daily_data[date]['amount'] for date in sorted_dates]

                        # 创建图表
                        fig, ax1 = plt.subplots(figsize=(10, 6))

                        # 格式化x轴日期
                        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
                        plt.xticks(rotation=45)

                        # 绘制时长柱状图
                        bars = ax1.bar(dates, hours, color=PRIMARY_COLOR, alpha=0.5, width=0.6)
                        ax1.set_xlabel('日期')
                        ax1.set_ylabel('时长(小时)', color=PRIMARY_COLOR)
                        ax1.tick_params(axis='y', labelcolor=PRIMARY_COLOR)

                        # 为柱状图添加数值标签
                        def add_labels(bars):
                            for bar in bars:
                                height = bar.get_height()
                                ax1.text(
                                    bar.get_x() + bar.get_width() / 2., height,
                                    f'{height:.1f}',
                                    ha='center', va='bottom', fontsize=8
                                )

                        add_labels(bars)

                        # 绘制金额折线图
                        ax2 = ax1.twinx()
                        ax2.plot(dates, amounts, 'o-', color=SECONDARY_COLOR, linewidth=2)
                        ax2.set_ylabel('金额(元)', color=SECONDARY_COLOR)
                        ax2.tick_params(axis='y', labelcolor=SECONDARY_COLOR)

                        # 设置标题和布局
                        plt.title(f'{student_name} 上课统计')
                        plt.tight_layout()

                        # 将图表添加到布局
                        self.chart_layout.add_widget(FigureCanvasKivyAgg(fig))

                    def create_overall_chart(self):
                        # 获取所有学生
                        students = self.db.get_all_students()

                        if not students:
                            self.chart_layout.add_widget(
                                CustomLabel(
                                    text='没有学生数据可供显示',
                                    size_hint=(1, 1),
                                    halign='center',
                                    valign='middle',
                                    font_size=HEADER_FONT
                                )
                            )
                            return

                        # 计算每个学生的统计数据
                        student_stats = []
                        for student in students:
                            student_id = student[0]
                            student_name = student[1]
                            summary = self.db.get_student_summary(student_id)

                            if summary[0] > 0:  # 只显示有课程记录的学生
                                student_stats.append({
                                    'name': student_name,
                                    'lessons': summary[0],
                                    'hours': summary[1],
                                    'amount': summary[2]
                                })

                        if not student_stats:
                            self.chart_layout.add_widget(
                                CustomLabel(
                                    text='没有课程记录可供显示',
                                    size_hint=(1, 1),
                                    halign='center',
                                    valign='middle',
                                    font_size=HEADER_FONT
                                )
                            )
                            return

                        # 按总金额排序
                        student_stats.sort(key=lambda x: x['amount'], reverse=True)

                        # 准备数据
                        names = [s['name'] for s in student_stats]
                        hours = [s['hours'] for s in student_stats]
                        amounts = [s['amount'] for s in student_stats]

                        # 创建图表
                        fig, ax1 = plt.subplots(figsize=(10, 6))

                        # 绘制时长柱状图
                        bars = ax1.bar(names, hours, color=PRIMARY_COLOR, alpha=0.5, width=0.6)
                        ax1.set_xlabel('学生')
                        ax1.set_ylabel('总时长(小时)', color=PRIMARY_COLOR)
                        ax1.tick_params(axis='y', labelcolor=PRIMARY_COLOR)

                        # 为柱状图添加数值标签
                        def add_labels(bars):
                            for bar in bars:
                                height = bar.get_height()
                                ax1.text(
                                    bar.get_x() + bar.get_width() / 2., height,
                                    f'{height:.1f}',
                                    ha='center', va='bottom', fontsize=8
                                )

                        add_labels(bars)

                        # 绘制金额折线图
                        ax2 = ax1.twinx()
                        ax2.plot(names, amounts, 'o-', color=SECONDARY_COLOR, linewidth=2)
                        ax2.set_ylabel('总金额(元)', color=SECONDARY_COLOR)
                        ax2.tick_params(axis='y', labelcolor=SECONDARY_COLOR)

                        # 设置标题和布局
                        plt.title('学生上课统计')
                        plt.xticks(rotation=45)
                        plt.tight_layout()

                        # 将图表添加到布局
                        self.chart_layout.add_widget(FigureCanvasKivyAgg(fig))

                    def filter_by_student(self, instance, value):
                        if value == '选择学生':
                            self.load_stats()
                        else:
                            # 获取学生ID
                            student_id = self.db.get_student_id_by_name(value)
                            if student_id:
                                self.load_stats(student_id)
                            else:
                                self.show_message('错误', '未找到该学生')

                    def export_data(self, instance):
                        if self.student_spinner.text == '选择学生':
                            # 导出所有记录
                            lessons = self.db.get_all_lessons()
                            if not lessons:
                                self.show_message('提示', '没有数据可导出')
                                return

                            df = pd.DataFrame(lessons,
                                              columns=['ID', '学生', '开始时间', '结束时间', '时长', '金额', '备注'])
                        else:
                            # 导出当前学生记录
                            student_id = self.db.get_student_id_by_name(self.student_spinner.text)
                            lessons = self.db.get_student_lessons(student_id)
                            if not lessons:
                                self.show_message('提示', '没有数据可导出')
                                return

                            df = pd.DataFrame(lessons, columns=['ID', '开始时间', '结束时间', '时长', '金额', '备注'])

                        # 保存为CSV
                        filename = f'class_stats_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                        df.to_csv(filename, index=False, encoding='utf-8-sig')
                        self.show_message('成功', f'数据已导出至 {filename}')

                    def go_back(self, instance):
                        self.manager.transition = SlideTransition(direction='right')
                        self.manager.current = 'main'

                    def show_message(self, title, message):
                        popup_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))

                        message_label = CustomLabel(
                            text=message,
                            size_hint_y=None,
                            height=dp(80),
                            halign='center',
                            valign='middle'
                        )

                        ok_btn = RoundedButton(text='确定')
                        ok_btn.bind(on_press=lambda instance: popup.dismiss())

                        popup_layout.add_widget(message_label)
                        popup_layout.add_widget(ok_btn)

                        popup = Popup(
                            title=title,
                            content=popup_layout,
                            size_hint=(0.7, 0.3),
                            auto_dismiss=False,
                            background_color=[0, 0, 0, 0.5]
                        )
                        popup.open()

                # 主应用类
                class ClassManagementApp(App):
                    def build(self):
                        # 初始化数据库
                        init_database()

                        # 创建屏幕管理器
                        sm = ScreenManager()

                        # 添加屏幕
                        sm.add_widget(MainScreen(name='main'))
                        sm.add_widget(StudentsScreen(name='students'))
                        sm.add_widget(LessonsScreen(name='lessons'))
                        sm.add_widget(StatsScreen(name='stats'))

                        return sm

                if __name__ == '__main__':
                    ClassManagementApp().run()
