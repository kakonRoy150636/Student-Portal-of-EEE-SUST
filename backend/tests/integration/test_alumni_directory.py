import pytest

pytestmark = pytest.mark.asyncio


async def test_postgres_partial_unique_index_allows_one_current_job(database):
    user_id = await database.user(role="alumni")
    profile = await database.conn.fetchval("""
        INSERT INTO alumni_profiles(user_id,batch_year,department,graduation_date,membership_status,is_visible,is_verified,verified_by_admin)
        VALUES ($1,2018,'EEE','2022-06-01','active',true,true,true) RETURNING id
    """, user_id.id)
    await database.conn.execute("""
        INSERT INTO alumni_employments(alumni_id,organization,position,sector,is_current)
        VALUES ($1,'First Org','Engineer','industry',true)
    """, profile)
    with pytest.raises(Exception) as error:
        await database.conn.execute("""
            INSERT INTO alumni_employments(alumni_id,organization,position,sector,is_current)
            VALUES ($1,'Second Org','Engineer','industry',true)
        """, profile)
    assert "uq_alumni_employments_one_current" in str(error.value)


async def test_postgres_batch_filter_and_summary(database, api):
    user = await database.user(role="student")
    profile = await database.conn.fetchval("""
        INSERT INTO alumni_profiles(user_id,batch_year,department,graduation_date,membership_status,is_visible,is_verified,verified_by_admin,current_country)
        VALUES ($1,2020,'EEE','2024-06-01','active',true,true,true,'Germany') RETURNING id
    """, user.id)
    await database.conn.execute("""
        INSERT INTO alumni_employments(alumni_id,organization,position,sector,country,is_current)
        VALUES ($1,'Global Systems','Engineer','industry','Germany',true)
    """, profile)
    response = await api.get('/api/v1/alumni/', params={'batch': 2020, 'country': 'Germany'}, headers=database.headers(user))
    assert response.status_code == 200, response.text
    assert response.json()['total'] == 1
    summary = await api.get('/api/v1/alumni/batches/2020/summary')
    assert summary.status_code == 200
    assert summary.json()['abroad'] == 1
