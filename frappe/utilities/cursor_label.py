from PyQt5.QtWidgets import QLabel, QHBoxLayout, QWidget, QSizePolicy
from frappe.widgets import lines


class CursorLabel:

    def __init__(self, parent) -> None:
        self.parent = parent
        self.container = QWidget(parent)
        self.h_box = QHBoxLayout()
        self.x_label = QLabel()
        self.y_label = QLabel()
        self.z_label = QLabel()
        self.t_label = QLabel()
        self.c_label = QLabel()
        self.value_label = QLabel()
        self.init_labels()

        self._x = 0
        self._y = 0
        self._z = 0
        self._t = 0
        self._c = 0
        self._value = 0

        self._physical_x = 1.0
        self._physical_y = 1.0
        self._physical_z = 1.0
        self._timestep = 1.0

        self._label_order = ["x", "y", "z", "t", "c"]

        self._has_x = False
        self._has_y = False
        self._has_z = False
        self._has_t = False
        self._has_c = False
        self._has_value = False

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, new_x):
        self._x = new_x
        self.refresh_labels()

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, new_y):
        self._y = new_y
        self.refresh_labels()

    @property
    def z(self):
        return self._z

    @z.setter
    def z(self, new_z):
        self._z = new_z
        self.refresh_labels()

    @property
    def t(self):
        return self._t

    @t.setter
    def t(self, new_t):
        self._t = new_t
        self.refresh_labels()

    @property
    def c(self):
        return self._c

    @c.setter
    def c(self, new_c):
        self._c = new_c
        self.refresh_labels()

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        self._value = new_value
        self.refresh_labels()

    @property
    def physical_x(self):
        return self._physical_x

    @physical_x.setter
    def physical_x(self, new_physical_x):
        self._physical_x = new_physical_x

    @property
    def physical_y(self):
        return self._physical_y

    @physical_y.setter
    def physical_y(self, new_physical_y):
        self._physical_y = new_physical_y

    @property
    def physical_z(self):
        return self._physical_z

    @physical_z.setter
    def physical_z(self, new_physical_z):
        self._physical_z = new_physical_z

    @property
    def timestep(self):
        return self._physical_z

    @timestep.setter
    def timestep(self, new_timestep):
        self._timestep = new_timestep

    @property
    def label_order(self):
        return self._label_order

    @property
    def has_x(self):
        return self._has_x

    @has_x.setter
    def has_x(self, has):
        self._has_x = has
        if self.has_x:
            self.x_label.show()
        else:
            self.x_label.hide()

    @property
    def has_y(self):
        return self._has_y

    @has_y.setter
    def has_y(self, has):
        self._has_y = has
        if self.has_y:
            self.y_label.show()
        else:
            self.y_label.hide()

    @property
    def has_z(self):
        return self._has_z

    @has_z.setter
    def has_z(self, has):
        self._has_z = has
        if self.has_z:
            self.z_label.show()
        else:
            self.z_label.hide()

    @property
    def has_t(self):
        return self._has_t

    @has_t.setter
    def has_t(self, has):
        self._has_t = has
        if self.has_t:
            self.t_label.show()
        else:
            self.t_label.hide()

    @property
    def has_c(self):
        return self._has_c

    @has_c.setter
    def has_c(self, has):
        self._has_c = has
        if self.has_c:
            self.c_label.show()
        else:
            self.c_label.hide()

    @property
    def has_value(self):
        return self._has_value

    @has_value.setter
    def has_value(self, has):
        self._has_value = has
        if self.has_value:
            self.value_label.show()
        else:
            self.value_label.hide()

    def get_labels(self):
        return [self.x_label, self.y_label, self.z_label, self.t_label,
                self.c_label]

    def get_values(self):
        return [self.x, self.y, self.z, self.t, self.c]

    def get_scaling_factors(self):
        return [self.physical_x, self.physical_y, self.physical_z,
                self.timestep, 1.0]

    def init_labels(self):
        label_size_policy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        label_size_policy.setRetainSizeWhenHidden(False)
        for label in self.get_labels():
            label.setSizePolicy(label_size_policy)
            self.h_box.addWidget(label)

        # self.value_label.setMinimumWidth(50)
        self.h_box.addWidget(self.value_label)
        self.container.setLayout(self.h_box)

    def refresh_labels(self):
        for label, q_label, value, scaling_factor in zip(
                self.label_order, self.get_labels(), self.get_values(),
                self.get_scaling_factors()):

            if label == "c":
                q_label_text = f"{label}: {value:.1f}"
            elif scaling_factor is not None:
                physical_value = value * scaling_factor
                q_label_text = f"{label}: {value:.1f}/{physical_value:.2f}"
            else:
                q_label_text = ""

            q_label.setText(q_label_text)

        self.value_label.setText(f"value: {self.value}")

    def setup_status_bar(self):
        self.parent.addPermanentWidget(lines.QVLine())
        self.parent.addPermanentWidget(self.container)
        # for q_label in self.get_labels():
        #     self.parent.addPermanentWidget(q_label)
        # self.parent.addPermanentWidget(self.value_label)

    def hide_and_show_labels(self):
        has_list = [self.has_x, self.has_y, self.has_z, self.has_t, self.has_c]
        for has_list_value, q_label in zip(has_list, self.get_labels()):
            if has_list_value:
                q_label.show()
            else:
                q_label.hide()

        self.value_label.show()

    def has_none(self):
        self.has_x, self.has_y, self.has_z, self.has_t, self.has_c, \
            self.has_value = False, False, False, False, False, False
