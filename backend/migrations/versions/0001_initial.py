from alembic import op
import sqlalchemy as sa
revision='0001_initial'; down_revision=None; branch_labels=None; depends_on=None

def upgrade():
    op.create_table('projects',sa.Column('id',sa.String(36),primary_key=True),sa.Column('name',sa.String(200),nullable=False),sa.Column('created_at',sa.DateTime(),nullable=False))
    op.create_table('datasets',sa.Column('id',sa.String(36),primary_key=True),sa.Column('project_id',sa.String(36),sa.ForeignKey('projects.id'),nullable=False),sa.Column('name',sa.String(200)),sa.Column('path',sa.Text()),sa.Column('format',sa.String(20)),sa.Column('rows',sa.Integer()),sa.Column('columns',sa.Integer()),sa.Column('created_at',sa.DateTime()))
    op.create_table('models',sa.Column('id',sa.String(36),primary_key=True),sa.Column('project_id',sa.String(36),sa.ForeignKey('projects.id'),nullable=False),sa.Column('name',sa.String(200)),sa.Column('task',sa.String(40)),sa.Column('architecture',sa.JSON()),sa.Column('created_at',sa.DateTime()))
    op.create_table('training_runs',sa.Column('id',sa.String(36),primary_key=True),sa.Column('project_id',sa.String(36),sa.ForeignKey('projects.id'),nullable=False),sa.Column('dataset_id',sa.String(36),sa.ForeignKey('datasets.id'),nullable=False),sa.Column('model_id',sa.String(36),sa.ForeignKey('models.id'),nullable=False),sa.Column('status',sa.String(20)),sa.Column('config',sa.JSON()),sa.Column('error',sa.Text()),sa.Column('started_at',sa.DateTime()),sa.Column('finished_at',sa.DateTime()))
    op.create_table('metrics',sa.Column('id',sa.String(36),primary_key=True),sa.Column('run_id',sa.String(36),sa.ForeignKey('training_runs.id'),nullable=False),sa.Column('epoch',sa.Integer()),sa.Column('split',sa.String(20)),sa.Column('loss',sa.Float()),sa.Column('metric',sa.Float()),sa.Column('learning_rate',sa.Float()),sa.Column('samples_per_sec',sa.Float()))
    op.create_table('checkpoints',sa.Column('id',sa.String(36),primary_key=True),sa.Column('run_id',sa.String(36),sa.ForeignKey('training_runs.id'),nullable=False),sa.Column('epoch',sa.Integer()),sa.Column('path',sa.Text()),sa.Column('is_best',sa.Boolean()),sa.Column('created_at',sa.DateTime()))
    op.create_table('model_versions',sa.Column('id',sa.String(36),primary_key=True),sa.Column('model_id',sa.String(36),sa.ForeignKey('models.id'),nullable=False),sa.Column('run_id',sa.String(36),sa.ForeignKey('training_runs.id'),nullable=False),sa.Column('version',sa.Integer()),sa.Column('checkpoint_path',sa.Text()),sa.Column('metrics',sa.JSON()),sa.Column('created_at',sa.DateTime()))
    op.create_table('evaluations',sa.Column('id',sa.String(36),primary_key=True),sa.Column('run_id',sa.String(36),sa.ForeignKey('training_runs.id'),nullable=False),sa.Column('metrics',sa.JSON()),sa.Column('created_at',sa.DateTime()))

def downgrade():
    for t in ['evaluations','model_versions','checkpoints','metrics','training_runs','models','datasets','projects']: op.drop_table(t)
