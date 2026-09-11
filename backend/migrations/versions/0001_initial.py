"""Initial organization scoped domain store.

Revision ID: 0001
"""
from alembic import op
import sqlalchemy as sa
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('organizations', sa.Column('id', sa.String(36), primary_key=True), sa.Column('name', sa.String(200), nullable=False), sa.Column('data', sa.JSON, nullable=False))
    op.create_table('users', sa.Column('id', sa.String(36), primary_key=True), sa.Column('org_id', sa.String(36), nullable=False), sa.Column('email', sa.String(254), nullable=False, unique=True), sa.Column('password_hash', sa.Text, nullable=False))
    op.create_index('ix_users_org_id', 'users', ['org_id'])
    op.create_table('sessions', sa.Column('token_hash', sa.String(64), primary_key=True), sa.Column('user_id', sa.String(36), nullable=False), sa.Column('org_id', sa.String(36), nullable=False), sa.Column('expires', sa.Float, nullable=False))
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'])
    op.create_index('ix_sessions_org_id', 'sessions', ['org_id'])
    op.create_table('invitations', sa.Column('token_hash', sa.String(64), primary_key=True), sa.Column('org_id', sa.String(36), nullable=False), sa.Column('email', sa.String(254), nullable=False), sa.Column('expires', sa.Float, nullable=False), sa.Column('used', sa.Integer, nullable=False))
    op.create_index('ix_invitations_org_id', 'invitations', ['org_id'])
    op.create_table('records', sa.Column('id', sa.String(36), primary_key=True), sa.Column('org_id', sa.String(36), nullable=False), sa.Column('kind', sa.String(40), nullable=False), sa.Column('work_id', sa.String(36), nullable=True), sa.Column('dedupe', sa.String(200), nullable=True), sa.Column('data', sa.JSON, nullable=False), sa.Column('created', sa.Float, nullable=False), sa.UniqueConstraint('org_id', 'kind', 'dedupe'))
    op.create_index('ix_records_org_id', 'records', ['org_id'])
    op.create_index('ix_record_scope', 'records', ['org_id', 'kind', 'work_id'])


def downgrade():
    for name in ('records', 'invitations', 'sessions', 'users', 'organizations'):
        op.drop_table(name)
