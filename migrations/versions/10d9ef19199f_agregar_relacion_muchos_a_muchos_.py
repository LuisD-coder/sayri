from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '10d9ef19199f'
down_revision = 'a0889640369f'
branch_labels = None
depends_on = None


def upgrade():
    # Crear tabla usuario_grupo con nombres explícitos
    op.create_table('usuario_grupo',
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('grupo_id', sa.Integer(), nullable=False),
        sa.Column('fecha_asignacion', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['grupo_id'], ['grupo.id'], name='fk_usuario_grupo_grupo_id'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], name='fk_usuario_grupo_usuario_id'),
        sa.PrimaryKeyConstraint('usuario_id', 'grupo_id', name='pk_usuario_grupo')
    )
    
    # Agregar constraint único al nombre del grupo (si no existe)
    with op.batch_alter_table('grupo', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_grupo_nombre', ['nombre'])


def downgrade():
    # Eliminar constraint único del nombre
    with op.batch_alter_table('grupo', schema=None) as batch_op:
        batch_op.drop_constraint('uq_grupo_nombre', type_='unique')
    
    # Eliminar tabla usuario_grupo
    op.drop_table('usuario_grupo')