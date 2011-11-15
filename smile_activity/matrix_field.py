# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 Smile. All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import datetime

from osv import osv, fields



class matrix(fields.dummy):
    """ A custom field to prepare data for, and mangle data from, the matrix widget.
    """

    ## Utility methods

    def _date_to_str(self, date):
        return date.strftime('%Y%m%d')

    def _is_date(self, date):
        return isinstance(date, (datetime.date, datetime.datetime))

    def _str_to_date(self, date):
        """ Transform string date to a proper date object
        """
        if not self._is_date(date):
            date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        return date

    def _get_prop(self, obj, prop_name, default_value=None):
        """ Get a property value
        """
        if not prop_name:
            return default_value
        prop_value = getattr(obj, prop_name, default_value)
        if prop_value is None:
            raise osv.except_osv('Error !', "%r has no %s property." % (obj, prop_name))
        return prop_value

    def _get_title_or_id(self, obj):
        """ Return the title of the object or a descriptive string
        """
        return getattr(obj, 'name', None) or getattr(obj, 'title', None) or 'Untitled (ID: %s)' % obj.id


    ## Native methods

    def _fnct_read(self, obj, cr, uid, ids, field_name, args, context=None):
        """ Dive into object lines and cells, and organize their info to let the matrix widget understand them
        """
        # Get the matrix parameters
        # TODO: guess line_type, cell_type and resource_type based on their xxx_property parameter counterparts
        # XXX Haven't found a cleaner way to get my matrix parameters... Any help is welcome ! :)
        # Property name from which we get the lines composing the matrix
        line_property = self.__dict__.get('line_property', None)
        line_type = self.__dict__.get('line_type', None)
        # Get line properties from which we derive the matrix resources
        line_resource_property_list = self.__dict__.get('line_resource_property_list', None)
        default_widget_type = self.__dict__.get('default_widget_type', 'float')
        dynamic_widget_type_property = self.__dict__.get('dynamic_widget_type_property', None)
        # Property name from which we get the cells composing the matrix.
        # Cells are fetched from the lines as defined above.
        cell_property = self.__dict__.get('cell_property', None)
        cell_type = self.__dict__.get('cell_type', None)
        cell_value_property = self.__dict__.get('cell_value_property', None)
        # Property name of the relation field on which we'll call the date_range property
        date_range_property = self.__dict__.get('date_range_property', None)
        active_date_range_property = self.__dict__.get('active_date_range_property', None)
        # The format we use to display date labels
        date_format = self.__dict__.get('date_format', None)
        # The object type we use to create new rows
        resource_type = self.__dict__.get('resource_type', None)
        # Additional classes can be manually added
        css_class = self.__dict__.get('css_class', [])

        # Check that all required parameters are there
        for p_name in ['line_property', 'line_type', 'line_resource_property_list', 'cell_property', 'cell_type', 'cell_value_property']:
            if not p_name:
                raise osv.except_osv('Error !', "%s parameter is missing." % p_name)

        # line_resource_property_list required at least one parameter
        if type(line_resource_property_list) != type([]) or len(line_resource_property_list) < 1:
            raise osv.except_osv('Error !', "line_resource_property_list parameter must be a list with at least one element.")

        # Browse through all objects on which our matrix field is defined
        matrix_list = {}
        for base_object in obj.browse(cr, uid, ids, context):
            matrix_data = []

            # Get the date range composing the timeline either on the current object or another one through a property
            date_range_property_object = base_object
            if date_range_property:
                date_range_property_object = self._get_prop(base_object, date_range_property)
            date_range = self._get_prop(date_range_property_object, 'date_range')
            if type(date_range) is not type([]):
                raise osv.except_osv('Error !', "date_range must return data that looks like selection field data.")

            # Get the list of all objects new rows of the matrix can be linked to
            # Keep the original order defined in matrix properties
            resource_value_list = []
            for (res_id, res_type) in line_resource_property_list:
                p = base_object.pool.get(res_type)
                resource_value_list.append({
                    'id': res_id,
                    'values': [(o.id, self._get_title_or_id(o)) for o in p.browse(cr, uid, p.search(cr, uid, [], context=context), context)],
                    })

            # Browse all lines that will compose our matrix
            lines = getattr(base_object, line_property, [])
            for line in lines:
                # Transfer some line data to the matrix widget
                line_data = {
                    'id': line.id,
                    'name': self._get_title_or_id(line),

                    # Is this resource required ?
                    # FIX: 'required': getattr(getattr(line, line_resource_property), 'required', False),

                    }

                # Get the type of the widget we'll use to display cell values
                line_data.update({'widget': self._get_prop(line, dynamic_widget_type_property, default_widget_type)})

                # Get all resources of the line
                # Keep the order defined by matrix field's properties
                res_list = []
                for (res_id, res_type) in line_resource_property_list:
                    res = self._get_prop(line, res_id)
                    res_list.append({
                        'id': res_id,
                        'label': self._get_title_or_id(res),
                        'value': res.id,
                        })
                line_data.update({'resources': res_list})

                # Get all cells of the line
                cells = getattr(line, cell_property, [])
                cells_data = {}
                for cell in cells:
                    cell_date = datetime.datetime.strptime(cell.date, '%Y-%m-%d')
                    cells_data[cell_date.strftime('%Y%m%d')] = getattr(cell, cell_value_property)
                line_data.update({'cells_data': cells_data})
                matrix_data.append(line_data)

            # Get default cells and their values for the template row.
            template_cells_data = {}
            # Get active date range. Default is to let all dates active.
            active_date_range = self._get_prop(date_range_property_object, active_date_range_property, date_range)
            for d in active_date_range:
                if not self._is_date(d):
                    raise osv.except_osv('Error !', "%s must return a list of dates." % active_date_range_property)
            # TODO: Add a "default_cell_value" method of some sort ?
            default_template_value = 0.0
            template_cells_data = dict([(self._date_to_str(d), default_template_value) for d in active_date_range])
            template_resources = [{
                    'id': res_id,
                    'label': res_id.replace('_', ' ').title(),
                    'value': 0,
                    } for (res_id, res_type) in line_resource_property_list]
            # Add a row template at the end
            matrix_data.append({
                'id': "template",
                'name': "Row template",
                'widget': default_widget_type,
                'cells_data': template_cells_data,
                'resources': template_resources,
                })

            # Pack all data required to render the matrix
            matrix_def = {
                'matrix_data': matrix_data,
                'date_range': [self._date_to_str(d) for d in date_range],  # Format our date range for our matrix # XXX Keep them as date objects ?
                'resource_value_list': resource_value_list,
                'column_date_label_format': date_format,
                'class': css_class,
                }

            if self.__dict__.get('experimental_slider', False):
                matrix_def['class'] = matrix_def['class'] + ['slider']

            matrix_list.update({base_object.id: matrix_def})
        return matrix_list



def get_matrix_conf(osv_instance):
    """ Utility method to get the configuration of the matrix field defined on the class the provided object is an instance of.
        XXX only one matrix field is allowed per object class.
    """
    field_defs = osv_instance.__dict__['_columns'].values()
    matrix_fields = [f for f in field_defs if f.__dict__.get('_fnct', None) and f.__dict__['_fnct'].im_class.__module__ == 'smile_activity.matrix_field']
    if not len(matrix_fields):
        return None
    elif len(matrix_fields) > 1:
        raise osv.except_osv('Error !', "You can't define more than one Matrix field on an object.")
    return matrix_fields[0].__dict__


def parse_virtual_field_id(f_id):
    """ This utility method parse and validate virtual fields coming from the matrix
        Raise an exception if it tries to read a field that doesn't follow Matrix widget conventions.
        Return None for fields generated by the matrix but not usefull for data input.
        Valid matrix field names:
            * resource_list  (ignored)
            * res_XX_PROPERTY_ID
            * res_template_PROPERTY_ID  (ignored)
            * res_dummyXX_PROPERTY_ID  (ignored)
            * cell_XX_YYYYMMDD
            * cell_template_YYYYMMDD  (ignored)
        XXX Can we increase the readability of the validation rules embedded in this method by using reg exps ?
    """
    f_id_elements = f_id.split('_')
    if (f_id.startswith('cell_template_') and len(f_id_elements) == 3) or \
       (f_id.startswith('res_template_')  and len(f_id_elements) >  2) or \
       (f_id.startswith('res_dummy')      and len(f_id_elements) >  2) or \
       (f_id.startswith('resource_list_') and len(f_id_elements) >  2):
        return None
    elif (f_id_elements[0] == 'cell' and len(f_id_elements) == 3) or (f_id_elements[0] == 'res' and len(f_id_elements) > 2):
        # For ressource, the last parameter is the property ID of the line the resource belong to. Recompose it
        if f_id_elements[0] == 'res':
            f_id_elements = f_id_elements[:2] + ['_'.join(f_id_elements[2:])]
            # TODO: check that the PROPERTY_ID (aka f_id_elements[2]) exist as a column in the line data model
        # Check that the date is valid
        if f_id_elements[0] == 'cell':
            date_element = f_id_elements[2]
            try:
                datetime.datetime.strptime(date_element, '%Y%m%d').date()
            except ValueError:
                raise osv.except_osv('Error !', "Field %r doesn't has an invalid %r date element." % (f_id, date_element))
        # Check that that the second element is an integer. It is allowed to starts with the 'new' prefix.
        id_element = f_id_elements[1]
        if id_element.startswith('new'):
            id_element = id_element[3:]
        if str(int(id_element)) == id_element:
            return f_id_elements
    # Requested field doesn't follow matrix convention
    raise osv.except_osv('Error !', "Field %r doesn't respect matrix widget conventions." % f_id)


def matrix_read_patch(func):
    """
    Let the matrix read the temporary fields that are not persistent in database.
    """
    def read_matrix_virtual_fields(*arg, **kw):
        result = func(*arg, **kw)
        obj = arg[0]
        cr = arg[1]
        uid = arg[2]
        ids = arg[3]
        fields = arg[4]
        context = kw.get('context', None)
        conf = get_matrix_conf(obj)
        if isinstance(ids, (int, long)):
            result = [result]
        updated_result = []
        cell_pool = obj.pool.get(conf['cell_type'])
        line_pool = obj.pool.get(conf['line_type'])
        for props in result:
            unread_fields = set(fields).difference(set(props.keys()))
            for f_id in unread_fields:
                f_id_elements = parse_virtual_field_id(f_id)
                if f_id_elements:
                    field_value = None
                    if not f_id_elements[1].startswith('new'):
                        line_id = int(f_id_elements[1])
                        if f_id_elements[0] == 'cell':
                            cell_date = datetime.datetime.strptime(f_id_elements[2], '%Y%m%d')
                            cell_id = cell_pool.search(cr, uid, [('date', '=', cell_date), ('line_id', '=', line_id)], limit=1, context=context)
                            if cell_id:
                                cell = cell_pool.browse(cr, uid, cell_id, context)[0]
                                field_value = getattr(cell, conf['cell_value_property'])
                        elif f_id_elements[0] == 'res':
                            if line_id:
                                resource_property = f_id_elements[2]
                                line = line_pool.browse(cr, uid, line_id, context)
                                field_value = getattr(line, resource_property).id
                    props.update({f_id: field_value})
            updated_result.append(props)
        if isinstance(ids, (int, long)):
            updated_result = updated_result[0]
        return updated_result
    return read_matrix_virtual_fields



def matrix_write_patch(func):
    """
    """
    def write_matrix_virtual_fields(*arg, **kw):
        result = func(*arg, **kw)
        obj = arg[0]
        cr = arg[1]
        uid = arg[2]
        ids = arg[3]
        vals = arg[4]
        context = kw.get('context', None)
        conf = get_matrix_conf(obj)
        # Automaticcaly remove out of range cells if dates changes
        if 'start_date' in vals or 'end_date' in vals:
            obj.update_cells(cr, uid, ids, context)

        written_lines = []
        for report in obj.browse(cr, uid, ids, context):

            # Regroup fields by lines
            lines = {}
            for (f_id, f_value) in vals.items():
                # Ignore non-matrix cells
                if not(f_id.startswith('res_') or f_id.startswith('cell_')):
                    continue
                f_id_elements = parse_virtual_field_id(f_id)
                line_id = f_id_elements[1]
                line_data = lines.get(line_id, {})
                line_data.update({f_id: f_value})
                lines[line_id] = line_data

            # Write data of each line
            for (line_id, line_data) in lines.items():
                # Separate line resources and line cells
                line_resources = dict([(parse_virtual_field_id(f_id)[2], int(v)) for (f_id, v) in line_data.items() if f_id.startswith('res_')])
                line_cells = dict([(datetime.datetime.strptime(parse_virtual_field_id(f_id)[2], '%Y%m%d'), v) for (f_id, v) in line_data.items() if f_id.startswith('cell_')])
                # Are we updating an existing line or creating a new one ?
                if line_id.startswith('new'):
                    line_vals = line_resources
                    line_vals.update({conf['line_inverse_property']: report.id})
                    line_id = obj.pool.get(conf['line_type']).create(cr, uid, line_vals, context)
                line_id = int(line_id)
                written_lines.append(line_id)

                # Save cells data
                for (cell_date, cell_value) in line_cells.items():
                    # Prepare the cell value
                    cell_vals = {
                        conf['cell_value_property']: cell_value,
                        }
                    # Search for an existing cell at the given date
                    cell = obj.pool.get(conf['cell_type']).search(cr, uid, [('date', '=', cell_date), ('line_id', '=', line_id)], context=context, limit=1)
                    # Cell doesn't exists, create it
                    if not cell:
                        cell_vals.update({
                            'date': cell_date,
                            'line_id': line_id,
                            })
                        obj.pool.get(conf['cell_type']).create(cr, uid, cell_vals, context)
                    # Update cell with our data
                    else:
                        cell_id = cell[0]
                        obj.pool.get(conf['cell_type']).write(cr, uid, cell_id, cell_vals, context)

        # If there was no references to one of our line it means it was deleted
        for report in obj.browse(cr, uid, ids, context):
            removed_lines = list(set([l.id for l in report.line_ids]).difference(set(written_lines)))
            obj.pool.get(conf['line_type']).unlink(cr, uid, removed_lines, context)

        return result

    return write_matrix_virtual_fields
