import collections
import os
import sys
from unittest import mock
import zipfile

import pytest
import pandas as pd

import cnb


@pytest.fixture
def canvas_course():
    "Returns a CanvasCourse object with a mocked Canvas connection"
    with mock.patch("cnb.canvasapi.Canvas"):
        canvas_course = cnb.CanvasCourse(
            course_id=123,
            canvas_url='foo',
            canvas_token='bar',
        )
        yield canvas_course


@mock.patch("cnb.canvasapi.Canvas")
class TestConnect:
    "Set up connection with different config methods"

    def test_connect_env(self, MockCanvas):
        "Set up connection with environtment variables"

        os.environ['CANVAS_URL'] = 'foo'
        os.environ['CANVAS_TOKEN'] = 'bar'

        c = cnb.CanvasConnection()

        MockCanvas.assert_called_with("foo", "bar")
        assert c.connection == MockCanvas()

    @mock.patch("cnb.configparser.ConfigParser")
    def test_connect_config(self, MockParser, MockCanvas):
        "Set up connection with an ini file"

        cparser = MockParser()
        setattr(cparser, 'read', lambda ini: None)
        cparser.__getitem__.return_value = {
            'CANVAS_URL': 'foo', 'CANVAS_TOKEN': 'bar'
        }

        c = cnb.CanvasConnection()

        MockCanvas.assert_called_with("foo", "bar")
        assert c.connection == MockCanvas()

    def test_connect_arg(self, MockCanvas):
        "Set up connection with call arguments"

        c = cnb.CanvasConnection(canvas_url='foo', canvas_token='bar')

        MockCanvas.assert_called_with("foo", "bar")
        assert c.connection == MockCanvas()

    def test_list_courses(self, MockCanvas):
        "List your courses on Canvas"

        c = cnb.CanvasConnection(canvas_url='foo', canvas_token='bar')
        c.list_courses()

        assert c.connection.get_courses.called

    def test_verify_connection(self, MockCanvas, capsys):
        os.environ['CANVAS_URL'] = 'foo'
        os.environ['CANVAS_TOKEN'] = 'bar'
        sys.argv[1:] = ['-c', '1000', '--verify']
        with mock.patch('cnb.exit') as mock_exit:
            cnb.main()
        std = capsys.readouterr()
        assert std.out == "Connecting to foo as bar\n"
        mock_exit.assert_called()


class TestWithFixture:
    def test_get_students(self, canvas_course):
        canvas_course.get_students_as_df()
        assert canvas_course.course.get_users.called_with(role="student")

    def test_download_students(self, canvas_course):

        mock_get_students_as_df = mock.MagicMock()
        canvas_course.get_students_as_df = mock_get_students_as_df

        canvas_course.download_students()

        mock_get_students_as_df().to_csv.assert_called_with(
            "students.csv", index=False
        )

    def test_init_downloads_area(self, canvas_course):
        with mock.patch("cnb.pathlib.Path") as MockPath:
            canvas_course.nbgrader.init_downloads_area('foo')

        MockPath.assert_called_with(f"downloaded/foo/archive")
        assert MockPath().mkdir.called_with(exist_ok=True)

    test_data = dict(
        attachments=[{'url': '...files/7/download/foo.ipynb'}],
        user_id=88,
        grade=None,
    )
    @pytest.mark.parametrize(
        'test_data',
        [
            test_data,
        ]
    ) 
    @mock.patch('cnb.requests.get')
    @mock.patch('cnb.zipfile')
    @mock.patch('cnb.has_attachments')
    def test_download_submissions_with_attachments(
        self, mock_has_attachments, mock_zipfile, mock_get, test_data, canvas_course
    ):
        # Given

        mock_zipfile.ZIP_DEFLATED = zipfile.ZIP_DEFLATED

        canvas_course.generate_unique_filename = mock.MagicMock()
        canvas_course.aget_downloads = mock.MagicMock()

        canvas_course.student_names = {88: 'yo ho'}

        submission = mock.MagicMock(**test_data)
        mock_has_attachments.return_value = [submission]

        # When
        canvas_course.download_submissions_with_attachments(
            7, "lab_name", ["nb_name"], filters=[cnb.ungraded]
        )

        # Then
        canvas_course.generate_unique_filename.assert_called_with(
            submission,
            'nb_name.ipynb'
        )
        mock_zipfile.ZipFile.assert_called_with(
            "downloaded/lab_name/archive/submissions.zip", "w",
            compression=zipfile.ZIP_DEFLATED
        )

    @pytest.mark.parametrize(
        "test_data",
        [
            (
                "upload_name.ipynb",
                "nb_name.ipynb",
                "http://xyz/files/2/download...",
                1,
                "Doe, Jane",
                "doejane_1_2_nb_name.ipynb",
            ),
            (
                "upload_name.ipynb",
                "nb_name.ipynb",
                "http://xyz/files/4/download...",
                3,
                "Doe, John",
                "doejohn_3_4_nb_name.ipynb",
            ),
            (
                "assignment_3.ipynb",
                "nb_name.ipynb",
                "http://xyz/files/6/download...",
                5,
                "Mehta, Tanvi",
                "mehtatanvi_5_6_nb_name.ipynb",
            ),
        ],
    )
    def test_unique(self, canvas_course, test_data):
        upload_name, nb_name, url, user_id, user_name, expected = test_data
        submission = mock.MagicMock()
        submission.user_id = user_id
        student = mock.MagicMock()
        student.sortable_name = user_name

        canvas_course.students = {user_id: student}
        submission.attachments = [
            dict(display_name=f"{upload_name}.ipynb", url=url)
        ]
        canvas_course.canvas.connection.get_course().get_user().sortable_name \
            = user_name
        assert (
            canvas_course.generate_unique_filename(submission, nb_name)
            == expected
        )

    def test_name(self, canvas_course):
        canvas_course.course.name = 'foo'
        assert str(canvas_course) == 'foo'


class TestIterators:
    def test_has_attachments(self):
        submission_with = mock.MagicMock(name="with", attachments=["foo"])
        submission_without = mock.MagicMock(name="without", spec=[])
        submissions = [submission_with, submission_without]

        calculated = list(cnb.has_attachments(submissions))
        expected = [submission_with]

        assert calculated == expected

    def test_ungraded(self):
        Submission = collections.namedtuple('Submission', 'id grade')
        submissions = [
            Submission(1, 'ok'),
            Submission(2, None),
            Submission(3, 'not ok'),
            Submission(4, None),
        ]
        assert list(cnb.ungraded(submissions)) \
            == [submissions[1], submissions[3]]

    def test_has_url(self):
        submission_with = mock.MagicMock(name="with")
        submission_with.url = "http://x"
        submission_without = mock.MagicMock(name="without")
        submission_without.url = None
        submissions = [submission_with, submission_without]
        assert list(cnb.has_url(submissions)) == [submission_with]

    def test_get_attachment_urls(self):
        submission = mock.MagicMock(name="attachments")
        url = mock.MagicMock(url='foo.com')
        submission.attachments = [{'url': url}]
        assert list(cnb.get_attachment_urls([submission, submission])) \
            == [url, url]

    def test_isub(self, canvas_course):
        mock_assignment = mock.MagicMock()
        mock_submission = mock.MagicMock()
        mock_assignment.get_submissions.return_value = [mock_submission]

        canvas_course.course.get_assignment.return_value = mock_assignment

        s = canvas_course.isubmissions(7)

        assert list(s) == [mock_submission]


class TestConfig:
    @mock.patch.dict("cnb.os.environ", {"config_file": "foo"})
    def test_env(self):
        config = cnb.get_config()
        assert config.get("config_file") == "foo"

    def test_conf(self):
        sys.argv[1:] = ['-i', 'foo.ini']

        config = cnb.get_config(config='foo.ini')
        assert config.get("config") == "foo.ini"


class TestMain:

    def test_undefined(self, capsys):
        sys.argv[1:] = []
        with mock.patch('cnb.exit') as mock_exit:
            cnb.main()
        std = capsys.readouterr()
        assert std.out == 'Course-id undefined\n'
        mock_exit.assert_called()

    @mock.patch('cnb.canvasapi.Canvas')
    def test_list_students(self, MockCanvas, capsys, canvas_course):
        os.environ['CANVAS_URL'] = 'foo'
        os.environ['CANVAS_TOKEN'] = 'bar'
        sys.argv[1:] = ['-c', '123', '-l']
        with mock.patch('cnb.CanvasCourse') as MockCourse:

            canvas_course.student_names = {1: 'John Doe', 23: 'Jane Moe'}
            MockCourse.return_value = canvas_course
            cnb.main()

        std = capsys.readouterr()
        assert std.out == '    1 John Doe\n   23 Jane Moe\n'

    @mock.patch('cnb.has_attachments')
    @mock.patch('cnb.has_url')
    @mock.patch('cnb.canvasapi.Canvas')
    def test_list_ungraded(
            self, MockCanvas, has_att, has_url, capsys, canvas_course
    ):
        os.environ['CANVAS_URL'] = 'foo'
        os.environ['CANVAS_TOKEN'] = 'bar'

        submission = mock.MagicMock(
            user_id=23,
            url='foo.html',
            attachments=[{'url': 'bar.ipynb'}],
        )
        has_url.return_value = [submission]
        has_att.return_value = [submission]

        sys.argv[1:] = ['-c', '123', '-a', '45']
        with mock.patch('cnb.CanvasCourse') as MockCourse:

            canvas_course.student_names = {1: 'John Doe', 23: 'Jane Moe'}
            MockCourse.return_value = canvas_course
            cnb.main()

        assert has_url.called
        std = capsys.readouterr()
        assert std.out == 'Jane Moe 23 foo.html\nJane Moe 23 bar.ipynb\n'


class TestSandbox:
    def test_init1(self):
        sys.argv[1:] = ['--course-id', '329']
        with mock.patch('cnb.CanvasCourse') as mock_cc:
            cnb.main()
        mock_cc.assert_called()

    def test_init2(self):
        sys.argv[1:] = ['-c', '329']
        with mock.patch('cnb.CanvasCourse') as mock_cc:
            cnb.main()
        mock_cc.assert_called()

    def test_init3(self):
        sys.argv[1:] = ['-c', '329']
        with mock.patch('cnb.get_config') as mock_config:
            mock_config.return_value = {
                'course_id': 329,
                'canvas_url': None,
                'canvas_token': None
            }
            with pytest.raises(cnb.ConfigError):
                cnb.main()

    def test_init4(self):
        sys.argv[1:] = ['-c', '329']
        with mock.patch('cnb.get_config') as mock_config:
            mock_config.return_value = {
                'course_id': 329,
                'canvas_url': 'foo',
                'canvas_token': None
            }
            with pytest.raises(cnb.TokenError):
                cnb.main()


class TestNBG:

    @mock.patch('cnb.subprocess')
    def test_import(self, mock_subprocessing, canvas_course):
        canvas_course.nbgrader.import_students()
        mock_subprocessing.run.assert_called_with(
            ['nbgrader', 'db', 'student', 'import', 'students.csv']
        )

    def test_read(self, canvas_course):
        with mock.patch('cnb.pd.read_csv') as mock_read_csv:
            grades = pd.DataFrame(
                dict(
                    assignment=[1, 2],
                    student_id=[3, 4],
                    score=[5, 6],
                )
            )
            mock_read_csv.return_value = grades
            gs = canvas_course.get_nbgrader_grades(assignment=2)

        assert mock_read_csv.called_with('grades.csv')
        expected = pd.Series([6], index=[4], name='score')
        assert all(gs == expected)
        assert gs.name == expected.name

    def test_upgrade(self, canvas_course, capsys):
        submission = mock.MagicMock(
            user_id=88
        )
        submissions = [submission]

        canvas_course.update_to_pass(submissions)

        assert submission.edit().called_with(
            submission={'posted_grade': 'complete'}
        )
