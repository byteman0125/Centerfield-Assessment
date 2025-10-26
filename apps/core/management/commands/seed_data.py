from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
import random

from apps.core.models import UserProfile
from apps.calls.models import WakeUpCall

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the database with demo users and wake-up calls'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=30,
            help='Number of demo wake-up calls to create (default: 30)'
        )
    
    def handle(self, *args, **options):
        count = options['count']
        
        self.stdout.write(f'Creating {count} demo wake-up calls...')
        
        # Create demo users if they don't exist
        demo_users = []
        
        for i in range(1, 11):  # Create 10 demo users
            username = f'demo_user_{i}'
            email = f'demo{i}@example.com'
            phone_number = f'+1555000{i:04d}'
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'phone_number': phone_number,
                    'is_phone_verified': True,
                    'is_staff': i == 1  # Make first user an admin
                }
            )
            
            if created:
                user.set_password('demo123')
                user.save()
                self.stdout.write(f'Created user: {username}')
            
            # Create or update profile
            profile, profile_created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'role': 'admin' if i == 1 else 'user',
                    'zip_code': f'{10000 + i * 100}',
                    'preferred_contact_method': random.choice(['call', 'sms']),
                    'timezone': 'America/New_York'
                }
            )
            
            demo_users.append(user)
        
        # Create demo wake-up calls
        zip_codes = ['10001', '90210', '33101', '60601', '75201', '98101', '80201', '85001', '30301', '37201']
        statuses = ['scheduled', 'completed', 'cancelled']
        contact_methods = ['call', 'sms']
        
        created_calls = 0
        
        for i in range(count):
            user = random.choice(demo_users)
            
            # Create calls in the past, present, and future
            days_offset = random.randint(-7, 7)  # Past week to future week
            hours_offset = random.randint(0, 23)
            minutes_offset = random.choice([0, 15, 30, 45])
            
            scheduled_time = timezone.now() + timedelta(
                days=days_offset,
                hours=hours_offset,
                minutes=minutes_offset
            )
            
            # Don't schedule calls in the past unless they're completed/cancelled
            if scheduled_time < timezone.now():
                status = random.choice(['completed', 'cancelled'])
            else:
                status = 'scheduled'
            
            wakeup_call = WakeUpCall.objects.create(
                user=user,
                scheduled_time=scheduled_time,
                phone_number=user.phone_number,
                contact_method=random.choice(contact_methods),
                zip_code=random.choice(zip_codes),
                status=status,
                is_demo=True,  # Mark as demo calls
            )
            
            created_calls += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_calls} demo wake-up calls'
            )
        )
        
        # Create one admin user for testing
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'phone_number': '+15551234567',
                'is_phone_verified': True,
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write('Created admin user: admin (password: admin123)')
        
        admin_profile, created = UserProfile.objects.get_or_create(
            user=admin_user,
            defaults={
                'role': 'admin',
                'zip_code': '10001',
                'preferred_contact_method': 'call',
                'timezone': 'America/New_York'
            }
        )
        
        self.stdout.write(
            self.style.SUCCESS('\nDemo data created successfully!')
        )
        self.stdout.write('\nDemo users created:')
        self.stdout.write('- demo_user_1 (admin) - password: demo123')
        self.stdout.write('- demo_user_2 through demo_user_10 - password: demo123')
        self.stdout.write('\nAdmin user:')
        self.stdout.write('- admin - password: admin123')
