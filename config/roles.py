from rolepermissions.roles import AbstractUserRole


class Admin(AbstractUserRole):
    available_permissions = {}


class Partner(AbstractUserRole):
    available_permissions = {}
