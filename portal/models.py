
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from sqlalchemy_continuum import make_versioned, versioning_manager
from sqlalchemy_continuum.plugins import FlaskPlugin, PropertyModTrackerPlugin

db = SQLAlchemy()

make_versioned(plugins=[FlaskPlugin()])
versioning_manager.plugins.append(PropertyModTrackerPlugin())


class TimeTrackedModel(db.Model):
    __abstract__ = True

    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                                                 server_default=func.now(), onupdate=func.now())
