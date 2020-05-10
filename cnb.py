#!/usr/bin/env python
"""
canvas-nbgrader facilitates exchange of data between Canvas LMS and nbgrader
"""
import argparse
import configparser
import functools
import os
import pathlib
import re
import subprocess
import zipfile

import requests
import pandas as pd
import canvasapi

__version__ = "0.0.1"

PASS = "\033[32mPASSED\033[00m"
FAIL = "\033[31mFAILED\033[00m"


class ConfigError(Exception):
    pass


class TokenError(Exception):
    pass


class CanvasConnection:
    def __init__(self, **config):
        cfg = get_config(**config)
        if cfg['canvas_url'] is None:
            raise ConfigError('canvas_url not defined')
        if cfg['canvas_token'] is None:
            raise TokenError('canvas_token not defined')
        self.connection = canvasapi.Canvas(
            cfg['canvas_url'], cfg['canvas_token']
        )

    def list_courses(self):
        for course in self.connection.get_courses():
            print(course.id, course.name)


class CanvasCourse:
    def __init__(self, **config):
        self.config = get_config(**config)

        self.canvas = CanvasConnection(**config)
        self.course_id = self.config['course_id']
        self.course = self.canvas.connection.get_course(self.course_id)
        self.student_names = {s.id: s.sortable_name for s in self.students()}

    def __str__(self):
        return self.course.name

    @functools.lru_cache()
    def students(self):
        """
        Return students for course from CanvasAPI
        """
        return self.course.get_users(enrollment_type=['student'])

    def download_students(self):
        """
        Download students registered as a csv file for import with nbgrader
        """
        self.get_students_as_df().to_csv('students.csv', index=False)
        print("Student list saved as students.csv")

    def get_students_as_df(self) -> pd.DataFrame:
        """
        Return students registered  as pandas dataframe
        """
        students = self.students()
        ids = [s.id for s in students]
        names = [s.sortable_name for s in students]
        emails = [getattr(s, 'login_id', None) for s in students]
        df = pd.DataFrame({
            'id': ids,
            'last_name': [n.split(', ')[0] for n in names],
            'first_name': [n.split(', ')[1] for n in names],
            'email': emails,
        })
        return df

    def init_lab(self, lab: str):
        """
        Assignment name in nbgrader

        :param lab:
            NBgrader name
        """
        self.lab = lab

    def download_submissions_with_attachments(
            self, assignment_id: int, nb_name: str
            ):
        """
        Create zipfile of submission attachments as in Canvas web client"

        :param assignment_id:
            Assignment ID
        :param nb_name:
            NBgrader assignment name
        """
        submissions = has_attachments(self.isubmissions(assignment_id))
        with zipfile.ZipFile(
            f'downloaded/{nb_name}/archive/submissions.zip', 'w',
            compression=zipfile.ZIP_DEFLATED
        ) as zp:
            for i, submission in enumerate(sorted(
                submissions, key=lambda s:
                self.student_names[s.user_id]
            ), start=1):
                attachment = submission.attachments[0]
                r = requests.get(attachment['url'])
                filename = self.generate_unique_filename(
                    submission, nb_name + ".ipynb"
                )
                zp.writestr(filename, r.text)
                print(
                    f'{i}. {self.student_names[submission.user_id]}:'
                    f' {filename}'
                )
        print(f'-> downloaded/{nb_name}/archive/submissions.zip')

    def isubmissions(self, assignment_id):
        assignment = self.course.get_assignment(assignment_id)
        for submission in assignment.get_submissions():
            yield submission

    def generate_unique_filename(self, submission, nb_name):
        s = submission

        file_id = re.search(
            r'files/(\d+)/download',
            s.attachments[0]['url']
        ).group(1)

        course = self.canvas.connection.get_course(submission.course_id)
        user = course.get_user(submission.user_id)
        last, first = user.sortable_name.split(', ')
        lastfirst = f"{last}{first}".replace(' ', '').lower()

        new_name = f"{lastfirst}_{s.user_id}_{file_id}_{nb_name}"
        return new_name

    def get_nbgrader_grades(self, assignment=None, csv_file='grades.csv'):
        """
        Read grades from nbgrader database, exported as 'grades.csv' file
        """
        df = pd.read_csv(csv_file)
        if assignment is not None:
            df = df[df.assignment == assignment]

        return df.set_index('student_id')['score']

    def get_lms_grades(self, assignment_id: int):
        """
        Get current grades for assignment
        """
        assignment = self.course.get_assignment(assignment_id)
        lms_grades = pd.Series(
            {
                student.id: assignment.get_submission(student).grade
                for student in self.students()
            },
            name='lms_grades'
        )
        lms_grades.index.set_names('student_id', inplace=True)

        return lms_grades

    def update_grades(self, submissions):
        for submission in submissions:
            print(submission.user_id, PASS)
            submission.edit(submission={'posted_grade': 'complete'})


class NBGraderInterface():

    def import_students(self):
        """
        Import students to nbgrader

        Call: 'nbgrader db student import students.csv'
        """
        subprocess.run('nbgrader db student import students.csv'.split())

    def init_downloads_area(self, lab):
        """
        Initialize nbgrader downloads directory
        """
        path = pathlib.Path(f'downloaded/{lab}/archive')
        path.mkdir(parents=True, exist_ok=True)


def has_attachments(submissions):
    """
    Filter submissions with attachments

    :param submissions:
        iterable
    :return:
        iterable over submissions with attachments
    """
    return filter(lambda s: hasattr(s, 'attachments'), submissions)


def ungraded(submissions):
    """
    Filter submissions that are ungraded

    :param submissions:
        iterable
    :return:
        iterable over ungraded submissions
    """
    return filter(lambda s: s.grade is None, submissions)


def has_url(submissions):
    """
    Filter submissions with url

    :param submissions:
        iterable
    :return:
        iterable over submissions with url
    """
    return filter(lambda s: bool(s.url), submissions)


def get_attachment_urls(submissions):
    return (s.attachments[0]['url'] for s in submissions)


def get_config(**args):
    """
    Set up configuration using priority order
        1  command line: represented by input variable args
        2  environment variables
        3  configuration file (config.ini)
        4 default settings (dictonary defined below)

    Returns dict with config options in lower case.
    """

    default = {
        'canvas_url': None,
        'canvas_token': None,
        'config_file': 'config.ini',
    }

    args_config = {k: v for k, v in args.items() if v is not None}
    env_config = {
        k.lower(): v
        for k, v in os.environ.items()
        if k.lower() in default
    }

    cparser = configparser.ConfigParser()
    config_file = {**default, **env_config, **args_config}['config_file']
    cparser.read(config_file)
    cconfig = {k.lower(): v for k, v in cparser['DEFAULT'].items()}

    config = {**default, **cconfig, **env_config, **args_config}

    return config


def command_line_args():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c', '--course-id', type=int, default=None, help='Course ID'
    )
    parser.add_argument(
        '-a', '--assignment', default=None, help='Assignment ID'
    )
    parser.add_argument(
        '-l', '--list-students', action='store_true', help='List Students'
    )
    parser.add_argument(
        '-i', '--config-file', default=None, help='List Students'
    )
    parser.add_argument(
        '-v', '--verify', action='store_true', help='Verify connection'
    )

    return parser.parse_args().__dict__


def list_students(c):
    for sid, name in c.student_names.items():
        print(f'{sid:5d} {name}')


def list_ungraded(c, assignment_id):
    for s in has_url(ungraded(c.isubmissions(assignment_id))):
        print(c.student_names[s.user_id], s.user_id, s.url)

    for s in has_attachments(ungraded(c.isubmissions(assignment_id))):
        print(c.student_names[s.user_id], s.user_id, s.attachments[0]['url'])


def main():

    args = command_line_args()
    config = get_config(**args)

    if 'course_id' not in config:
        print("Course-id undefined")
        exit()
    else:
        c = CanvasCourse(**config)

    if args['list_students']:
        list_students(c)

    if args['assignment']:
        list_ungraded(c, args['assignment'])

    if args['verify']:
        print(
            f"Connected to {config['canvas_url']} as {config['canvas_token']}"
        )


if __name__ == "__main__":
    main()
