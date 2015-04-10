# figgy

figgy is sample code for interviews that relates to some of the code in our content management system.

As a prospective applicant you have two options for submitting a job application:

The first is to develop your own solution and submit a pull request that we will review (You can also submit your solution as a patch if you don’t wish to have your solution public on Git).  Also, if you haven’t done so, submit a resume and cover letter through our corporate site.

Alternatively, you may review any of the currently closed pull requests in this repo.  The closed requests are a mixture of past applications, and your challenge is to pick out one approach that you would submit in lieu your own solution.  Apply through the listing for a Python engineer on our corporate site and tell us what your chosen approach would be and why.

Pull requests to make the setup process or documentation smoother are more than welcome.


# Python
 
## Setup

### System dependencies

* virtualenv (`sudo easy_install virtualenv`)

### Very first time

This setup assumes you have just cloned the git repo and are in the directory with this `README.md`.

    $ virtualenv ve --python=python2.7 --prompt="(figgy)"  # Get a set of eggs just for this
    $ . ve/bin/activate                                    # Turn on the virtualenv
    $ python setup.py develop --always-unzip               # Fill the virtualenv with Python dependencies
    $ cp figgy/local.py.example figgy/local.py             # Your local.py is your personal settings. Edit them later.
    $ python manage.py syncdb --noinput                    # Fill out the database schema
    $ python manage.py createsuperuser                     # Establish an admin so you can log in
    $ python manage.py runserver                           # Prove this works by visiting http://localhost:8000

Before you write any code, make sure you can run the tests and get them to pass 100%.

### Every time

When you come back to work after a day or more, you'll need to update your git checkout, and make
sure you have any new dependencies or schema modifications:

    $ . ve/bin/activate                           # Turn on the virtualenv (Every time!)
    $ python setup.py develop --always-unzip      # Update the virtualenv with new Python dependencies
    $ python manage.py syncdb --noinput           # Make sure the database schema is still filled out
    $ python manage.py runserver                  # Prove this works by visiting http://localhost:8000

tc.

## Tests

The tests for this project are managed by `tox`, a Python package.
First, install `tox` via `easy_install` (or `pip`).

Prior to running tox, be sure to create a `figgy/_local_tests.py` file by copying
`figgy/_local_tests.py.example` to `figgy/_local_tests.py`.  Any modifications to the test settings
should be performed in the developer's `_local_test.py`.

To run the tests:

    tox

The first run will take a while as it builds a virtualenv and installs everything in it, subsequent
ones will be much faster.  To rebuild the virtualenv later with updated dependencies:

    tox -r

You normally shouldn't need to recreate the tox virtualenv, since it updates itself on each run,
but it might be necessary in cases of version conflicts.


## Importing test data
Import the initial set of test data.

````
$ python manage.py process_data_file data/initial/*.xml
````

## The Task

You received an initial set of data with very loose specs and created a basic database to manage it with. The second round of updates blew away your assumptions about how the data was formed and you are now getting a better picture. Can you implement a solution to handle the xml updates?

* Feel free to do any code modifications you feel that will accomplish your task. This includes adding additional modules, models, etc.
* Please note that the update data potentially holds bad and conflicting values.



````
$ python manage.py process_data_file data/update/*.xml
````

