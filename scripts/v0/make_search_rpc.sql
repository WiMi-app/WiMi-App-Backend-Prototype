CREATE OR REPLACE FUNCTION search_users(p_search_term TEXT)
RETURNS TABLE(id UUID, username TEXT, full_name TEXT, avatar_url TEXT[], email TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT
        u.id,
        u.username::TEXT,
        u.full_name::TEXT,
        u.avatar_url,
        u.email::TEXT
    FROM
        users AS u,
        websearch_to_tsquery('simple', p_search_term) AS query,
        to_tsvector('simple', u.username || ' ' || u.full_name) AS document
    WHERE
        document @@ query
    ORDER BY
        ts_rank(document, query) DESC
    LIMIT 10;
END;
$$ LANGUAGE plpgsql;