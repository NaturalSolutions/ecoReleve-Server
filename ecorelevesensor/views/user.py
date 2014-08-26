"""
Created on Mon Aug 25 15:35:40 2014

@author: Natural Solutions (Thomas)
"""

from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.view import view_config
from sqlalchemy import select
from ecorelevesensor.models.security import User
from ecorelevesensor.models import DBSession

@view_config(
    route_name='core/user',
    permission=NO_PERMISSION_REQUIRED,
    renderer='json'
)
def users(request):
    """Return the list of all the users with their ids.
    """
    query = select([
        User.pk_id,
        User.fullname.label('fullname')
    ]).order_by(User.lastname, User.firstname)
    return [dict(row) for row in DBSession.execute(query).fetchall()]