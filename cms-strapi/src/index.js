'use strict';

module.exports = {
  /**
   * An asynchronous register function that runs before
   * your application is initialized.
   *
   * This gives you an opportunity to extend code.
   */
  register(/*{ strapi }*/) {},

  /**
   * An asynchronous bootstrap function that runs before
   * your application gets started.
   *
   * This gives you an opportunity to set up your data model,
   * run jobs, or perform some special logic.
   */
  async bootstrap({ strapi }) {
    // Ensure Public role has permissions to read pages
    if (process.env.NODE_ENV === 'development') {
      try {
        const publicRole = await strapi
          .query('plugin::users-permissions.role')
          .findOne({ where: { type: 'public' } });

        if (publicRole) {
          const permissions = await strapi
            .query('plugin::users-permissions.permission')
            .findMany({
              where: {
                role: publicRole.id,
                action: {
                  $in: ['api::page.page.find', 'api::page.page.findOne'],
                },
              },
            });

          const existingActions = permissions.map((p) => p.action);
          const actionsToEnable = ['api::page.page.find', 'api::page.page.findOne'].filter(
            (action) => !existingActions.includes(action)
          );

          if (actionsToEnable.length > 0) {
            await Promise.all(
              actionsToEnable.map((action) =>
                strapi.query('plugin::users-permissions.permission').create({
                  data: {
                    action,
                    role: publicRole.id,
                  },
                })
              )
            );
            console.log(`[Bootstrap] Enabled Public role permissions: ${actionsToEnable.join(', ')}`);
          }
        }
      } catch (error) {
        console.warn('[Bootstrap] Could not set Public role permissions:', error.message);
      }

      // Run seed script automatically in development (idempotent)
      // Note: Seed script must be run manually via npm run seed:demo-home
      // or via external script - bootstrap can't easily execute ES modules
      console.log('[Bootstrap] To seed demo content, run: npm run seed:demo-home');
    }

    // Migrate old cards-rows layout values to new format
    try {
      const pages = await strapi.entityService.findMany('api::page.page', {
        populate: ['sections'],
      });

      let migratedCount = 0;
      const layoutMigration = {
        'two-equal': 'two-50-50',
        'two-2-3': 'two-60-40',
        'two-1-3': 'two-75-25',
      };

      for (const page of pages) {
        if (!page.sections || !Array.isArray(page.sections)) continue;

        let modified = false;
        const updatedSections = page.sections.map((section) => {
          if (section.__component === 'blocks.cards-rows' && section.rows && Array.isArray(section.rows)) {
            const updatedRows = section.rows.map((row) => {
              if (row.layout && layoutMigration[row.layout]) {
                modified = true;
                return { ...row, layout: layoutMigration[row.layout] };
              }
              return row;
            });
            if (modified) {
              return { ...section, rows: updatedRows };
            }
          }
          return section;
        });

        if (modified) {
          await strapi.entityService.update('api::page.page', page.id, {
            data: { sections: updatedSections },
          });
          migratedCount++;
          console.log(`[Bootstrap] Migrated cards-rows layouts for page: ${page.slug || page.id}`);
        }
      }

      if (migratedCount > 0) {
        console.log(`[Bootstrap] Migrated ${migratedCount} page(s) with old cards-rows layouts`);
      }
    } catch (error) {
      console.warn('[Bootstrap] Could not migrate cards-rows layouts:', error.message);
    }
  },
};


