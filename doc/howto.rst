HOWTO
=====

Initial setup
-------------

* A connection with the CanvasAPI requires a valid url and an access token
  These are preferrably set as environment variables or in a config.ini file::

    
    # config.ini
    [DEFAULT]
    CANVAS_URL=https://site.instructure.com
    CANVAS_TOKEN=longrandomstring

  Verify the connection with

    >>> import cnb
    >>> c = cnb.CanvasConnection(config_file="config.ini")
    >>> c.connection.get_current_user().name
    'Olav Vahtras'

* List defined courss
    >>> c.list_courses()

* nbgrader

    $ pip install nbgrader
    $ nbgrader quickstart course_id
    $ nbgrader generate assignment

extensions for jupyter

    $ jupyter nbextension install --sys-prefix --py nbgrader --overwrite
    $ jupyter nbextension enable --sys-prefix --py nbgrader
    $ jupyter serverextension enable --sys-prefix --py nbgrader
    
Workflow
--------

* In Canvas a course is defined and students are registered
  - There
* A local project folder for nbgrader is initialized
* Student roster are exported from Canvas to nbgrader
* Create an assignment in nbgrader
