import os
import numpy
from django.db import models
from django.template.defaultfilters import slugify
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.core.exceptions import ValidationError
from django.conf import settings

from h1ds_configdb import CONFIGDB_SUBFOLDER

PROPERTY_VALUE_TYPE_CHOICES = (
    ('FL', 'Float'),
    ('IN', 'Integer'),
    ('ST', 'String'),
    )

value_type_mapping = {
    str:'String',
    numpy.float64:'Float',
    float:'Float',
    int:'Integer',
    }

class ConfigDBLoadingDir(models.Model):
    """A folder on the server which is scanned for new and updated files.
    
    """
    folder = models.CharField(max_length=1024, help_text="Directory on server where new or updated files are to be found.")
    force_overwrite = models.BooleanField(default=False, help_text="If checked, files will be rescanned even if they already exist in database")

    def __unicode__(self):
        return self.folder

class ConfigDBFileType(models.Model):
    """Represents a type of configuration file.

    For example, VMEC, Poincare plot, etc. 
    As we specify  the mimetype, we implicitly assume  there should be
    different ConfigDBFileTypes for different mime types. For example,
    PNG and  SVG representations of  the same Poincare plot  will have
    different ConfigFBFileTypes.
    """

    name = models.CharField(max_length=256, help_text="Name of file type; e.g. Poincare plot")
    mimetype = models.CharField(max_length=126, help_text="MIME type; e.g. image/png")
    description = models.TextField(help_text="Provide a description of the file type for users.")
    slug = models.SlugField(help_text="Representation of file type for URL - note that this is autogenerated on save.")

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Overwrite slug on save.
        self.slug = slugify(self.name)
        super(ConfigDBFileType, self).save(*args, **kwargs)

class ConfigDBPropertyType(models.Model):
    """Property type of a configuration.

    For example, rotational transform, beta, etc...
    """
    name = models.CharField(max_length=256, help_text="Name of property type.")
    description = models.TextField(help_text="Provide a description for the property type for users.")
    slug = models.SlugField(help_text="Representation of file type for URL - note that this is autogenerated on save.")
    value_type = models.CharField(max_length=2, choices=PROPERTY_VALUE_TYPE_CHOICES, help_text="Type of the property values.")

    def save(self, *args, **kwargs):
        # Overwrite slug on save.
        self.slug = slugify(self.name)
        super(ConfigDBPropertyType, self).save(*args, **kwargs)

class ConfigDBProperty(models.Model):
    """Property associated with a configuration database file.

    """

    configdb_file = models.ForeignKey("ConfigDBFile", help_text="Configuartion database file to which this property is associated.")
    configdb_propertytype = models.ForeignKey(ConfigDBPropertyType, help_text="Select the property type.")
    
    # Only one of the value_ fields will be used in each instance.
    value_float = models.FloatField(blank=True, null=True)
    value_integer = models.IntegerField(blank=True, null=True)
    value_string = models.CharField(max_length=256, blank=True, null=True)
    
    def get_value(self):
        appropriate_value_type = 'value_'+self.configdb_propertytype.get_value_type_display().lower()
        return getattr(self, appropriate_value_type)

    class Meta:
        verbose_name_plural = "config db properties"

    # Override  save,  if  type  of  value is  different  to  that  of
    # configdb_propertytype.value_type, than raise an exception.
    def save(self, *args, **kwargs):
        appropriate_value_type = 'value_'+self.configdb_propertytype.get_value_type_display().lower()
        for attr in [i for i in dir(self) if i.startswith('value_')]:
            if attr == appropriate_value_type:
                if getattr(self, attr) == None:
                    raise ValidationError
        else:
                if getattr(self, attr) != None:
                    raise ValidationError                
        super(ConfigDBProperty, self).save(*args,**kwargs)

def configdb_filename(instance, filename):
    split_path = filename.split('/')
    n_dir_conf = len(settings.H1DS_CONFIGDB_DIR.split('/'))
    
    new_paths = [CONFIGDB_SUBFOLDER]
    new_paths.extend(split_path[n_dir_conf:])
    
    return os.path.join(*new_paths)

class ConfigDBFile(models.Model):
    dbfile = models.FileField(upload_to=configdb_filename)
    filetype = models.ForeignKey(ConfigDBFileType)
    md5sum = models.CharField(max_length=32)
    
"""
configdb_type_class_map = {
    str:ConfigDBStringProperty,
    numpy.float64:ConfigDBFloatProperty,
    float:ConfigDBFloatProperty,
    int:ConfigDBIntProperty
    }
"""
