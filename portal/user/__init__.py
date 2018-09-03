import enum


"""
Definition:
    1. A member is someone who has successfully authenticated.
    2. Someone is a member if they have an account in our system.
    3. Member is a set which encompasses all the roles below.

Here are the roles of whales.media
    1. Admin - able to see everything
    2. Support - financials, no passwords nor vps info
    3. Technician - passwords, vps, no financials
    4. Client - financials, no passwords, no vps
    5. Vendor - (later)

All the roles above are MEMBERS of whales.media.
"""

class RolesEnum(enum.Enum):
    ADMIN = 'admin'
    SUPPORT = 'support'
    TECHNICIAN = 'technician'
    CLIENT = 'client'

