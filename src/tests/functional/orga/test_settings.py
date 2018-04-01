from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils.timezone import now

from pretalx.event.models import Event
from pretalx.person.models import EventPermission


@pytest.mark.django_db
def test_edit_mail_settings(orga_client, event, availability):
    assert event.settings.mail_from != 'foo@bar.com'
    assert event.settings.smtp_port != '25'
    response = orga_client.get(
        event.orga_urls.mail_settings,
        follow=True,
    )
    assert response.status_code == 200
    response = orga_client.post(
        event.orga_urls.mail_settings,
        follow=True,
        data={
            'mail_from': 'foo@bar.com',
            'smtp_host': 'foo.bar.com',
            'smtp_password': '',
            'smtp_port': '25',
        }
    )
    assert response.status_code == 200
    event = Event.objects.get(pk=event.pk)
    assert event.settings.mail_from == 'foo@bar.com'
    assert event.settings.smtp_port == 25


@pytest.mark.django_db
def test_test_mail_settings(orga_client, event, availability):
    assert event.settings.mail_from != 'foo@bar.com'
    assert event.settings.smtp_port != '25'
    response = orga_client.get(
        event.orga_urls.mail_settings,
        follow=True,
    )
    assert response.status_code == 200
    response = orga_client.post(
        event.orga_urls.mail_settings,
        follow=True,
        data={
            'mail_from': 'foo@bar.com',
            'smtp_host': 'foo.bar.com',
            'smtp_password': '',
            'smtp_port': '25',
            'smtp_use_custom': '1',
            'test': '1',
        }
    )
    assert response.status_code == 200
    event = Event.objects.get(pk=event.pk)
    assert event.settings.mail_from == 'foo@bar.com'
    assert event.settings.smtp_port == 25


@pytest.mark.django_db
@pytest.mark.parametrize('path,allowed', (
    ('tests/functional/orga/fixtures/custom.css', True),
    ('tests/functional/orga/fixtures/malicious.css', False),
    ('tests/conftest.py', False),
))
def test_add_custom_css(event, orga_client, path, allowed):
    assert not event.custom_css
    with open(path, 'r') as custom_css:
        response = orga_client.post(
            event.orga_urls.edit_settings,
            {
                'name_0': event.name,
                'slug': 'csstest',
                'locales': ','.join(event.locales),
                'locale': event.locale,
                'is_public': event.is_public,
                'date_from': event.date_from,
                'date_to': event.date_to,
                'timezone': event.timezone,
                'email': event.email,
                'primary_color': event.primary_color,
                'custom_css': custom_css
            },
            follow=True
        )
    event.refresh_from_db()
    assert response.status_code == 200
    assert bool(event.custom_css) == allowed


@pytest.mark.django_db
def test_add_logo(event, orga_client):
    assert not event.logo
    response = orga_client.get(event.urls.base, follow=True)
    assert '<img "src="/media' not in response.content.decode()
    with open('../assets/icon.svg', 'rb') as logo:
        response = orga_client.post(
            event.orga_urls.edit_settings,
            {
                'name_0': event.name,
                'slug': 'logotest',
                'locales': event.locales,
                'locale': event.locale,
                'is_public': event.is_public,
                'date_from': event.date_from,
                'date_to': event.date_to,
                'timezone': event.timezone,
                'email': event.email,
                'primary_color': '#00ff00',
                'custom_css': None,
                'logo': logo,
            },
            follow=True
        )
    event.refresh_from_db()
    assert event.slug != 'logotest'
    assert event.primary_color == '#00ff00'
    assert response.status_code == 200
    assert event.logo
    response = orga_client.get(event.urls.base, follow=True)
    assert '<img src="/media' in response.content.decode(), response.content.decode()


@pytest.mark.django_db
def test_orga_cannot_create_event(orga_client):
    count = Event.objects.count()
    response = orga_client.post(
        reverse('orga:event.create'),
        {
            'name_0': 'The bestest event',
            'slug': 'testevent',
            'is_public': False,
            'date_from': now().strftime('%Y-%m-%d'),
            'date_to': (now() + timedelta(days=1)).strftime('%Y-%m-%d'),
            'timezone': 'UTC',
            'locale': 'en',
            'locales': ['en'],
            'email': 'orga@orga.org',
            'primary_color': None,
        },
        follow=True
    )
    assert response.status_code == 403
    assert not Event.objects.filter(slug='testevent').exists()
    assert Event.objects.count() == count


@pytest.mark.django_db
def test_create_event(superuser_client):
    count = Event.objects.count()
    response = superuser_client.get(reverse('orga:event.create'), follow=True)
    assert response.status_code == 200
    response = superuser_client.post(
        reverse('orga:event.create'),
        {
            'name_0': 'The bestest event',
            'slug': 'testevent',
            'is_public': False,
            'date_from': now().strftime('%Y-%m-%d'),
            'date_to': (now() + timedelta(days=1)).strftime('%Y-%m-%d'),
            'timezone': 'UTC',
            'locale': 'en',
            'locales': ['en'],
            'email': 'orga@orga.org',
            'primary_color': None,
        },
        follow=True
    )
    assert response.status_code == 200, response.content.decode()
    assert Event.objects.get(slug='testevent')
    assert Event.objects.count() == count + 1


@pytest.mark.django_db
def test_invite_orga_member(orga_client, event):
    assert EventPermission.objects.filter(event=event).count() == 1
    perm = EventPermission.objects.filter(event=event).first()
    response = orga_client.post(
        event.orga_urls.team_settings,
        {
            'permissions-TOTAL_FORMS': 2,
            'permissions-INITIAL_FORMS': 1,
            'permissions-0-invitation_email': '',
            'permissions-0-is_orga': 'on',
            'permissions-0-review_override_count': '0',
            'permissions-0-id': str(perm.id),
            'permissions-1-invitation_email': 'other@user.org',
            'permissions-1-is_orga': 'on',
            'permissions-1-review_override_count': '0',
            'permissions-1-id': '',
        }, follow=True,
    )
    assert response.status_code == 200
    assert EventPermission.objects.filter(event=event).count() == 2
    perm = EventPermission.objects.get(event=event, invitation_token__isnull=False)
    assert perm.is_orga
    assert not perm.is_reviewer


@pytest.mark.django_db
def test_remove_last_orga_member(orga_client, event):
    assert EventPermission.objects.filter(event=event).count() == 1
    perm = EventPermission.objects.filter(event=event).first()
    response = orga_client.post(
        event.orga_urls.team_settings,
        {
            'permissions-TOTAL_FORMS': 1,
            'permissions-INITIAL_FORMS': 1,
            'permissions-0-invitation_email': '',
            'permissions-0-is_orga': 'on',
            'permissions-0-review_override_count': '0',
            'permissions-0-id': str(perm.id),
            'permissions-0-DELETE': 'on',
        }, follow=True,
    )
    assert response.status_code == 200
    assert EventPermission.objects.filter(event=event).count() == 1


@pytest.mark.django_db
def test_retract_invitation(orga_client, event):
    perm = EventPermission.objects.filter(event=event).first()
    response = orga_client.post(
        event.orga_urls.team_settings,
        {
            'permissions-TOTAL_FORMS': 2,
            'permissions-INITIAL_FORMS': 1,
            'permissions-0-invitation_email': '',
            'permissions-0-is_orga': 'on',
            'permissions-0-review_override_count': '0',
            'permissions-0-id': str(perm.id),
            'permissions-1-invitation_email': 'other@user.org',
            'permissions-1-is_orga': 'on',
            'permissions-1-review_override_count': '0',
            'permissions-1-id': '',
        }, follow=True,
    )
    assert response.status_code == 200
    assert EventPermission.objects.filter(event=event).count() == 2
    perm_new = EventPermission.objects.get(event=event, invitation_token__isnull=False)
    response = orga_client.post(
        event.orga_urls.team_settings,
        {
            'permissions-TOTAL_FORMS': 2,
            'permissions-INITIAL_FORMS': 2,
            'permissions-0-invitation_email': '',
            'permissions-0-is_orga': 'on',
            'permissions-0-review_override_count': '0',
            'permissions-0-id': str(perm.id),
            'permissions-1-invitation_email': 'other@user.org',
            'permissions-1-is_orga': 'on',
            'permissions-1-review_override_count': '0',
            'permissions-1-id': str(perm_new.id),
            'permissions-1-DELETE': 'on',
        }, follow=True,
    )
    assert response.status_code == 200
    assert EventPermission.objects.filter(event=event).count() == 1


@pytest.mark.django_db
def test_add_orga_to_review(orga_client, event):
    perm = EventPermission.objects.get(event=event)
    assert perm.is_reviewer is False
    assert perm.is_orga is True
    response = orga_client.post(
        event.orga_urls.team_settings,
        {
            'permissions-TOTAL_FORMS': 1,
            'permissions-INITIAL_FORMS': 1,
            'permissions-0-invitation_email': '',
            'permissions-0-is_orga': 'on',
            'permissions-0-is_reviewer': 'on',
            'permissions-0-review_override_count': '0',
            'permissions-0-id': str(perm.id),
        }, follow=True,
    )
    assert response.status_code == 200
    perm.refresh_from_db()
    assert perm.is_reviewer is True
    assert perm.is_orga is True


@pytest.mark.parametrize('target', ('email', 'nick'))
@pytest.mark.django_db
def test_add_reviewer_to_orga(orga_client, review_user, event, target):
    review_perm = EventPermission.objects.get(event=event, is_orga=False)
    orga_perm = EventPermission.objects.get(event=event, is_orga=True)
    assert review_perm.is_reviewer is True
    assert review_perm.is_orga is False
    response = orga_client.post(
        event.orga_urls.team_settings,
        {
            'permissions-TOTAL_FORMS': 2,
            'permissions-INITIAL_FORMS': 2,
            'permissions-0-invitation_email': '',
            'permissions-0-is_orga': 'on',
            'permissions-0-review_override_count': '0',
            'permissions-0-id': str(orga_perm.id),
            'permissions-1-invitation_email': '',
            'permissions-1-is_orga': 'on',
            'permissions-1-is_reviewer': 'on',
            'permissions-1-review_override_count': '0',
            'permissions-1-id': str(review_perm.id),
        }, follow=True,
    )
    assert response.status_code == 200
    review_perm.refresh_from_db()
    assert review_perm.is_reviewer is True
    assert review_perm.is_orga is True


@pytest.mark.django_db
def test_activate_plugin(event, orga_client, monkeypatch):
    class Plugin:
        module = name = 'test_plugin'
        visible = True
        app = None

    monkeypatch.setattr('pretalx.common.plugins.get_all_plugins', lambda: [Plugin()])
    plugin_name = 'plugin:test_plugin'

    assert not event.plugins
    response = orga_client.post(
        event.orga_urls.plugins, follow=True,
        data={plugin_name: 'enable'},
    )
    assert response.status_code == 200
    event.refresh_from_db()
    assert event.plugins == 'test_plugin'
    response = orga_client.post(
        event.orga_urls.plugins, follow=True,
        data={plugin_name: 'disable'},
    )
    assert response.status_code == 200
    event.refresh_from_db()
    assert event.plugins == ''
