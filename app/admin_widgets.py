"""
Custom form widgets for Flask-Admin to fix rendering errors.
"""
from flask_admin.form.widgets import Select2Widget
from wtforms.widgets import Select

class FixedSelect2Widget(Select2Widget):
    """
    A fixed version of Select2Widget that properly formats choices
    to avoid the 'not enough values to unpack (expected 4, got 3)' error.
    """
    def __call__(self, field, **kwargs):
        # First check if choices have the correct format, fix if needed
        if hasattr(field, 'choices') and field.choices:
            # Create new choices list with properly formatted tuples
            new_choices = []
            for choice in field.choices:
                if isinstance(choice, tuple):
                    if len(choice) == 2:
                        # Convert 2-tuple to 4-tuple (value, label, selected, render_kw)
                        value, label = choice
                        selected = field.data == value
                        new_choices.append((value, label, selected, {}))
                    elif len(choice) == 3:
                        # Convert 3-tuple to 4-tuple
                        value, label, selected = choice
                        new_choices.append((value, label, selected, {}))
                    elif len(choice) == 4:
                        # Already properly formatted
                        new_choices.append(choice)
                    else:
                        # Unexpected format, convert to safe format
                        new_choices.append((str(choice[0]), str(choice[1]), False, {}))
                else:
                    # Not a tuple, convert to string and make a safe tuple
                    new_choices.append((str(choice), str(choice), False, {}))
            # Replace choices with fixed version
            field.choices = new_choices
        
        # Call parent method with fixed choices
        try:
            return super(FixedSelect2Widget, self).__call__(field, **kwargs)
        except Exception as e:
            # Fallback to base Select widget if Select2Widget fails
            from wtforms.widgets import Select
            return Select().__call__(field, **kwargs)

class SimpleSelectWidget(Select):
    """
    A basic select widget that doesn't use Select2 to avoid rendering issues.
    """
    def __call__(self, field, **kwargs):
        # First check if choices have the correct format, fix if needed
        if hasattr(field, 'choices') and field.choices:
            # Create new choices list with properly formatted tuples
            new_choices = []
            for choice in field.choices:
                if isinstance(choice, tuple):
                    if len(choice) == 2:
                        # Keep as 2-tuple for standard Select
                        new_choices.append(choice)
                    elif len(choice) == 3:
                        # Convert to 2-tuple for standard Select
                        value, label, _ = choice
                        new_choices.append((value, label))
                    elif len(choice) == 4:
                        # Convert to 2-tuple for standard Select
                        value, label, _, _ = choice
                        new_choices.append((value, label))
                    else:
                        # Unexpected format, convert to safe format
                        try:
                            new_choices.append((str(choice[0]), str(choice[1])))
                        except (IndexError, TypeError):
                            # Fallback for malformed tuples
                            new_choices.append((str(choice), str(choice)))
                else:
                    # Not a tuple, convert to string
                    new_choices.append((str(choice), str(choice)))
            # Replace choices with fixed version
            field.choices = new_choices
        
        # Call parent method with fixed choices
        return Select.__call__(self, field, **kwargs)
        
    # Override render_option to handle both 2-tuple and 4-tuple formats
    def render_option(self, value, label, selected, **kwargs):
        # Ensure kwargs is a dict, not a boolean
        if not isinstance(kwargs, dict):
            kwargs = {}
        return super(SimpleSelectWidget, self).render_option(value, label, selected, **kwargs)
