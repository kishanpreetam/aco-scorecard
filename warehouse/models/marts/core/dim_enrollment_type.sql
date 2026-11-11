select
    enrollment_type_code,
    enrollment_type_name,
    description,
    display_order
from {{ ref('enrollment_types') }}
