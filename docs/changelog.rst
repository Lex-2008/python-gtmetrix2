Recent changes
==============

.. currentmodule:: python_gtmetrix2

Note that according to `semver <https://semver.org/>`__, as long as major
version is 0, any breaking changes are possible.  When this library sees a
first user, its major version will be bumped to 1.

0.3.0
-----

* library wa split into modules for easier differentiation between public and
  private parts

0.2.0
-----

* Argument for the :meth:`Test.fetch` was renamed from ``wait_for_complete`` to
  ``wait_for_completion``
* Bugfix: :meth:`Test.fetch` was following redirects when it wasn't supposed
  to. Due to this, it was fetching "report" JSON and crashed.

0.1.2
-----

* Class ``Interface`` was renamed to :class:`Account`
* "GTmetrix" name was removed from exception names
* Docs: separate pages for changelog and contributing.

0.1.1
-----

* Added documentation
* Added :meth:`Interface.testFromId <Account.testFromId>` and
  :meth:`reportFromId <Account.reportFromId>` methods
* Changed the way how errors are checked - now :meth:`Requestor._plain_request`
  respect HTTP status instead of parsing the response JSON.
* Changed Travis config to deploy to both "test" and "main" pypi's

0.1.0
-----

Initial release

0.0.x
-----

Non-release versions (currently published to `test.pypi.org
<https://test.pypi.org/project/python-gtmetrix2/>`__). Last number in version
is build number in Travis and increases over time. Hence, recent 0.0.x versions
might be "newer" than some 0.1.x versions!
