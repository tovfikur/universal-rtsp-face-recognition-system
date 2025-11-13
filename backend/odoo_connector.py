"""
Odoo Integration Connector

This module handles all communication with Odoo ERP system via XML-RPC.
Supports:
- Employee synchronization (pull from Odoo)
- Attendance push to Odoo
- Bi-directional sync
"""

import xmlrpc.client
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import ssl


class OdooConnector:
    """
    Handles connection and data synchronization with Odoo ERP system.
    """

    def __init__(self, url: str, db: str, username: str, password: str):
        """
        Initialize Odoo connector.

        Args:
            url: Odoo server URL (e.g., 'http://localhost:8069')
            db: Odoo database name
            username: Odoo username/email
            password: Odoo password or API key
        """
        self.url = url.rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.models = None
        self.common = None

        # Setup logging
        self.logger = logging.getLogger(__name__)

    def connect(self) -> Dict[str, Any]:
        """
        Establish connection to Odoo and authenticate.

        Returns:
            Dict with success status and message
        """
        try:
            # Create SSL context that doesn't verify certificates (for local dev)
            # In production, remove this and use proper SSL certificates
            context = ssl._create_unverified_context()

            # Connect to common endpoint
            self.common = xmlrpc.client.ServerProxy(
                f'{self.url}/xmlrpc/2/common',
                context=context,
                allow_none=True
            )

            # Authenticate
            self.uid = self.common.authenticate(
                self.db,
                self.username,
                self.password,
                {}
            )

            if not self.uid:
                return {
                    "success": False,
                    "error": "Authentication failed. Check credentials."
                }

            # Connect to object endpoint
            self.models = xmlrpc.client.ServerProxy(
                f'{self.url}/xmlrpc/2/object',
                context=context,
                allow_none=True
            )

            self.logger.info(f"Connected to Odoo as user ID: {self.uid}")

            return {
                "success": True,
                "message": "Connected to Odoo successfully",
                "uid": self.uid
            }

        except Exception as e:
            self.logger.error(f"Odoo connection error: {e}")
            return {
                "success": False,
                "error": f"Connection failed: {str(e)}"
            }

    def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection and return server info.

        Returns:
            Dict with connection status and server version
        """
        try:
            if not self.common:
                return self.connect()

            version = self.common.version()

            return {
                "success": True,
                "message": "Connection test successful",
                "server_version": version.get('server_version'),
                "protocol_version": version.get('protocol_version')
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Connection test failed: {str(e)}"
            }

    def _execute_kw(self, model: str, method: str, args: list, kwargs: dict = None) -> Any:
        """
        Execute Odoo model method.

        Args:
            model: Odoo model name (e.g., 'hr.employee')
            method: Method name (e.g., 'search_read')
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Method result
        """
        if not self.uid or not self.models:
            raise Exception("Not connected to Odoo. Call connect() first.")

        if kwargs is None:
            kwargs = {}

        return self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            model,
            method,
            args,
            kwargs
        )

    def pull_employees(self, limit: int = 1000) -> Dict[str, Any]:
        """
        Pull employee data from Odoo.

        Args:
            limit: Maximum number of employees to fetch

        Returns:
            Dict with success status and employee list
        """
        try:
            # Search for active employees
            employees = self._execute_kw(
                'hr.employee',
                'search_read',
                [
                    [['active', '=', True]]  # Only active employees
                ],
                {
                    'fields': [
                        'id',
                        'name',
                        'work_email',
                        'mobile_phone',
                        'department_id',
                        'job_id',
                        'barcode',
                        'employee_type'
                    ],
                    'limit': limit
                }
            )

            # Transform Odoo data to our format
            persons = []
            for emp in employees:
                person = {
                    'person_id': emp.get('barcode') or f"ODOO_{emp['id']}",
                    'name': emp.get('name'),
                    'email': emp.get('work_email'),
                    'phone': emp.get('mobile_phone'),
                    'department': emp['department_id'][1] if emp.get('department_id') else None,
                    'position': emp['job_id'][1] if emp.get('job_id') else None,
                    'metadata': {
                        'odoo_id': emp['id'],
                        'employee_type': emp.get('employee_type'),
                        'synced_from_odoo': True,
                        'sync_date': datetime.now().isoformat()
                    }
                }
                persons.append(person)

            self.logger.info(f"Pulled {len(persons)} employees from Odoo")

            return {
                "success": True,
                "message": f"Successfully pulled {len(persons)} employees",
                "employees": persons,
                "total": len(persons)
            }

        except Exception as e:
            self.logger.error(f"Error pulling employees: {e}")
            return {
                "success": False,
                "error": f"Failed to pull employees: {str(e)}"
            }

    def push_attendance(self, attendance_records: List[Dict]) -> Dict[str, Any]:
        """
        Push attendance records to Odoo.

        Args:
            attendance_records: List of attendance records to push

        Returns:
            Dict with success status and sync results
        """
        try:
            pushed = 0
            failed = 0
            errors = []

            for record in attendance_records:
                try:
                    # Get employee by person_id (barcode or odoo_id)
                    person_id = record.get('person_id')

                    # Search for employee
                    employee_ids = self._execute_kw(
                        'hr.employee',
                        'search',
                        [[
                            '|',
                            ['barcode', '=', person_id],
                            ['id', '=', person_id.replace('ODOO_', '') if person_id.startswith('ODOO_') else 0]
                        ]],
                        {'limit': 1}
                    )

                    if not employee_ids:
                        failed += 1
                        errors.append(f"Employee not found: {person_id}")
                        continue

                    employee_id = employee_ids[0]

                    # Parse check-in time
                    check_in = datetime.fromisoformat(record['check_in'])
                    check_out = None
                    if record.get('check_out'):
                        check_out = datetime.fromisoformat(record['check_out'])

                    # Create check-in attendance
                    checkin_vals = {
                        'employee_id': employee_id,
                        'check_in': check_in.strftime('%Y-%m-%d %H:%M:%S'),
                    }

                    if check_out:
                        checkin_vals['check_out'] = check_out.strftime('%Y-%m-%d %H:%M:%S')

                    # Create attendance record in Odoo
                    attendance_id = self._execute_kw(
                        'hr.attendance',
                        'create',
                        [checkin_vals],
                        {}
                    )

                    if attendance_id:
                        pushed += 1
                        self.logger.info(f"Pushed attendance for {person_id}: Odoo ID {attendance_id}")
                    else:
                        failed += 1
                        errors.append(f"Failed to create attendance for {person_id}")

                except Exception as e:
                    failed += 1
                    errors.append(f"Error processing {record.get('person_id', 'unknown')}: {str(e)}")
                    self.logger.error(f"Error pushing attendance record: {e}")

            return {
                "success": True if pushed > 0 else False,
                "message": f"Pushed {pushed} attendance records, {failed} failed",
                "pushed": pushed,
                "failed": failed,
                "errors": errors if errors else None,
                "total": len(attendance_records)
            }

        except Exception as e:
            self.logger.error(f"Error pushing attendance: {e}")
            return {
                "success": False,
                "error": f"Failed to push attendance: {str(e)}"
            }

    def sync_employee_to_odoo(self, person_data: Dict) -> Dict[str, Any]:
        """
        Create or update employee in Odoo.

        Args:
            person_data: Person data from face attendance system

        Returns:
            Dict with success status
        """
        try:
            # Check if employee exists
            person_id = person_data.get('person_id')
            employee_ids = self._execute_kw(
                'hr.employee',
                'search',
                [['barcode', '=', person_id]],
                {'limit': 1}
            )

            # Prepare employee values
            employee_vals = {
                'name': person_data.get('name'),
                'barcode': person_id,
                'work_email': person_data.get('email'),
                'mobile_phone': person_data.get('phone'),
            }

            # Add department if exists
            if person_data.get('department'):
                # Search for department
                dept_ids = self._execute_kw(
                    'hr.department',
                    'search',
                    [['name', 'ilike', person_data['department']]],
                    {'limit': 1}
                )
                if dept_ids:
                    employee_vals['department_id'] = dept_ids[0]

            if employee_ids:
                # Update existing
                self._execute_kw(
                    'hr.employee',
                    'write',
                    [employee_ids, employee_vals],
                    {}
                )
                return {
                    "success": True,
                    "message": f"Updated employee in Odoo: {person_id}",
                    "odoo_id": employee_ids[0],
                    "action": "updated"
                }
            else:
                # Create new
                employee_id = self._execute_kw(
                    'hr.employee',
                    'create',
                    [employee_vals],
                    {}
                )
                return {
                    "success": True,
                    "message": f"Created employee in Odoo: {person_id}",
                    "odoo_id": employee_id,
                    "action": "created"
                }

        except Exception as e:
            self.logger.error(f"Error syncing employee to Odoo: {e}")
            return {
                "success": False,
                "error": f"Failed to sync employee: {str(e)}"
            }

    def get_attendance_records(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Get attendance records from Odoo for a date range.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Dict with success status and attendance records
        """
        try:
            records = self._execute_kw(
                'hr.attendance',
                'search_read',
                [[
                    ['check_in', '>=', f'{start_date} 00:00:00'],
                    ['check_in', '<=', f'{end_date} 23:59:59']
                ]],
                {
                    'fields': [
                        'id',
                        'employee_id',
                        'check_in',
                        'check_out',
                        'worked_hours'
                    ]
                }
            )

            return {
                "success": True,
                "message": f"Retrieved {len(records)} attendance records",
                "records": records,
                "total": len(records)
            }

        except Exception as e:
            self.logger.error(f"Error getting attendance records: {e}")
            return {
                "success": False,
                "error": f"Failed to get attendance records: {str(e)}"
            }
